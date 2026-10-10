import csv
import io
from datetime import datetime, timezone

from skin_cancer.webapp.extensions import db
from skin_cancer.webapp.models import (
    Analysis,
    AnalysisResult,
    DoctorReview,
    UploadBatch,
)

CSV_URL = "/api/upload-batches/{batch_id}/analysis.csv"


def csv_rows(response):
    text = response.data.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def test_analysis_csv_exports_latest_analysis_result_and_review(
    app, client, users, case_graph, login
):
    record = case_graph["own"]
    with app.app_context():
        old_analysis = db.session.get(Analysis, record["analysis_id"])
        old_analysis.status = "COMPLETED"
        db.session.add(
            AnalysisResult(
                analysis_id=old_analysis.id,
                model_name="old-model",
                binary_result=0,
                binary_probability=0.2,
                predicted_class="NV",
                predicted_probability=0.7,
                class_probabilities={"NV": 0.7},
                inference_time_ms=35.0,
            )
        )

        latest = Analysis(
            case_id=record["case_id"],
            case_image_id=record["image_id"],
            status="COMPLETED",
            lesion_area_px=125.5,
            lesion_perimeter_px=48.25,
            lesion_ratio=0.42,
            bbox_x=10,
            bbox_y=11,
            bbox_width=120,
            bbox_height=80,
            started_at=datetime(2026, 10, 10, 8, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(2026, 10, 10, 8, 0, 2, tzinfo=timezone.utc),
        )
        db.session.add(latest)
        db.session.flush()

        db.session.add_all(
            [
                AnalysisResult(
                    analysis_id=latest.id,
                    model_name="intermediate-model",
                    binary_result=0,
                    binary_probability=0.3,
                    predicted_class="BKL",
                    predicted_probability=0.6,
                    class_probabilities={"BKL": 0.6},
                    inference_time_ms=20.0,
                ),
                AnalysisResult(
                    analysis_id=latest.id,
                    model_name="EfficientNet-B0",
                    binary_result=1,
                    binary_probability=0.91,
                    predicted_class="MEL",
                    predicted_probability=0.83,
                    class_probabilities={
                        "MEL": 0.83,
                        "NV": 0.02,
                        "BCC": 0.03,
                        "AK": 0.04,
                        "BKL": 0.05,
                        "DF": 0.01,
                        "VASC": 0.01,
                        "SCC": 0.01,
                    },
                    inference_time_ms=18.75,
                ),
            ]
        )
        db.session.add_all(
            [
                DoctorReview(
                    case_id=record["case_id"],
                    analysis_id=latest.id,
                    doctor_id=users["doctor"],
                    doctor_conclusion="Bản nháp cũ",
                    review_status="DRAFT",
                ),
                DoctorReview(
                    case_id=record["case_id"],
                    analysis_id=latest.id,
                    doctor_id=users["doctor"],
                    clinical_note="Tổn thương không đối xứng",
                    doctor_conclusion="Cần loại trừ melanoma",
                    recommendation="Khám chuyên khoa và cân nhắc sinh thiết",
                    review_status="REVIEWED",
                ),
            ]
        )
        db.session.commit()
        latest_id = latest.id

    login("doctor")
    response = client.get(CSV_URL.format(batch_id=record["batch_id"]))

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert response.data.startswith(b"\xef\xbb\xbf")
    assert "batch_" in response.headers["Content-Disposition"]
    assert "analysis.csv" in response.headers["Content-Disposition"]
    rows = csv_rows(response)
    assert len(rows) == 1
    row = rows[0]
    assert row["analysis_id"] == str(latest_id)
    assert row["model_name"] == "EfficientNet-B0"
    assert row["ai_binary_result"] == "MALIGNANT"
    assert row["ai_binary_probability"] == "0.91"
    assert row["predicted_class"] == "MEL"
    assert row["probability_MEL"] == "0.83"
    assert row["lesion_area_px"] == "125.5"
    assert row["bbox_width"] == "120"
    assert row["review_status"] == "REVIEWED"
    assert row["doctor_conclusion"] == "Cần loại trừ melanoma"
    assert row["reviewer_name"] == "Doctor A"
    assert row["analysis_completed_at"] == "2026-10-10T08:00:02Z"
    assert "image_path" not in row


def test_analysis_csv_leaves_doctor_review_fields_empty(
    app, client, case_graph, login
):
    record = case_graph["own"]
    with app.app_context():
        analysis = db.session.get(Analysis, record["analysis_id"])
        db.session.add(
            AnalysisResult(
                analysis_id=analysis.id,
                model_name="test-model",
                binary_result=0,
                binary_probability=0.12,
                predicted_class="NV",
                predicted_probability=0.88,
            )
        )
        db.session.commit()

    login("doctor")
    response = client.get(CSV_URL.format(batch_id=record["batch_id"]))
    row = csv_rows(response)[0]

    assert row["ai_binary_result"] == "BENIGN"
    for column in (
        "review_status",
        "doctor_conclusion",
        "clinical_note",
        "recommendation",
        "reviewer_name",
        "review_updated_at",
    ):
        assert row[column] == ""


def test_analysis_csv_includes_rejected_batch_items(
    app, client, case_graph, login
):
    record = case_graph["own"]
    with app.app_context():
        batch = db.session.get(UploadBatch, record["batch_id"])
        batch.item_results = [
            {
                "original_filename": "broken.exe",
                "filename": None,
                "status": "FAILED",
                "error_message": "Định dạng file không được hỗ trợ",
            }
        ]
        batch.total_images = 2
        batch.failed_count = 1
        batch.status = "PARTIAL"
        db.session.commit()

    login("doctor")
    response = client.get(CSV_URL.format(batch_id=record["batch_id"]))
    rows = csv_rows(response)

    assert len(rows) == 2
    rejected = next(row for row in rows if row["original_filename"] == "broken.exe")
    assert rejected["image_status"] == "FAILED"
    assert rejected["image_error_message"] == "Định dạng file không được hỗ trợ"
    assert rejected["image_id"] == ""
    assert rejected["analysis_id"] == ""


def test_analysis_csv_empty_batch_has_headers(app, client, users, case_graph, login):
    with app.app_context():
        batch = UploadBatch(
            case_id=case_graph["own"]["case_id"],
            doctor_id=users["doctor"],
            total_images=0,
            status="COMPLETED",
        )
        db.session.add(batch)
        db.session.commit()
        batch_id = batch.id

    login("doctor")
    response = client.get(CSV_URL.format(batch_id=batch_id))

    assert response.status_code == 200
    assert csv_rows(response) == []
    header = response.data.decode("utf-8-sig").splitlines()[0]
    assert "ai_binary_result" in header
    assert "doctor_conclusion" in header
