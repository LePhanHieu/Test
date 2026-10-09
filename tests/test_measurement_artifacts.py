from pathlib import Path

from skin_cancer.webapp.extensions import db
from skin_cancer.webapp.models import Analysis
from skin_cancer.webapp.services.measurement_service import MeasurementResult


def test_successful_remeasurement_deletes_replaced_contour_after_commit(
    app, client, users, case_graph, login, monkeypatch
):
    measurement_root = Path(app.config["MEASUREMENT_FOLDER"])
    measurement_root.mkdir(parents=True, exist_ok=True)
    old_contour = measurement_root / "old.png"
    new_contour = measurement_root / "new.png"
    old_contour.write_bytes(b"old")
    new_contour.write_bytes(b"new")

    with app.app_context():
        analysis = db.session.get(Analysis, case_graph["own"]["analysis_id"])
        analysis.contour_path = str(old_contour)
        db.session.commit()

    result = MeasurementResult(
        status="COMPLETED",
        lesion_area_px=100.0,
        lesion_perimeter_px=40.0,
        lesion_ratio=0.25,
        bbox_x=1,
        bbox_y=2,
        bbox_width=10,
        bbox_height=12,
        contour_path=str(new_contour),
    )
    monkeypatch.setattr(
        "skin_cancer.webapp.routes.measurements.MeasurementService.measure",
        lambda _service, _source, _output: result,
    )

    login("doctor")
    token = client.get("/api/auth/csrf").get_json()["csrf_token"]
    response = client.post(
        f"/api/analyses/{case_graph['own']['analysis_id']}/measure",
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 200
    assert old_contour.exists() is False
    assert new_contour.exists() is True
    with app.app_context():
        analysis = db.session.get(Analysis, case_graph["own"]["analysis_id"])
        assert Path(analysis.contour_path) == new_contour
