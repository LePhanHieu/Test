from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Event
import os

from reportlab.platypus import Spacer

from skin_cancer.webapp.extensions import db
from skin_cancer.webapp.models import Analysis, Case, DoctorReview, Report, User
from skin_cancer.webapp.services.report_service import ReportService


def test_concurrent_report_generation_keeps_every_committed_pdf(
    app, users, case_graph, monkeypatch
):
    barrier = Barrier(2)

    def synchronized_build(_service, path, _case, _analysis, version):
        Path(path).write_bytes(f"report version {version}".encode())
        if version == 2:
            barrier.wait(timeout=5)

    monkeypatch.setattr(ReportService, "_build_pdf", synchronized_build)

    def generate_once():
        with app.app_context():
            case = db.session.get(Case, case_graph["own"]["case_id"])
            analysis = db.session.get(
                Analysis, case_graph["own"]["analysis_id"]
            )
            doctor = db.session.get(User, users["doctor"])
            try:
                report = ReportService(app).generate(case, analysis, doctor)
                return report.id
            finally:
                db.session.remove()

    with ThreadPoolExecutor(max_workers=2) as executor:
        report_ids = list(executor.map(lambda _index: generate_once(), range(2)))

    with app.app_context():
        reports = db.session.scalars(
            db.select(Report)
            .where(Report.id.in_(report_ids))
            .order_by(Report.report_version)
        ).all()
        assert [report.report_version for report in reports] == [2, 3]
        for report in reports:
            assert (Path(app.config["REPORT_FOLDER"]) / report.pdf_path).is_file()


def test_pdf_diagnosis_uses_the_persisted_review_author(
    app, users, case_graph, monkeypatch, tmp_path
):
    captured = {}

    with app.app_context():
        case = db.session.get(Case, case_graph["own"]["case_id"])
        analysis = db.session.get(Analysis, case_graph["own"]["analysis_id"])
        review = DoctorReview(
            case_id=case.id,
            analysis_id=analysis.id,
            doctor_id=users["admin"],
            doctor_conclusion="Reviewed by administrator",
            review_status="REVIEWED",
        )
        db.session.add(review)
        db.session.commit()

        service = ReportService(app)

        def capture_card(*, review, doctor):
            captured["review_id"] = review.id
            captured["doctor_name"] = doctor.full_name
            return Spacer(1, 1)

        monkeypatch.setattr(service, "_doctor_review_card", capture_card)
        service._build_pdf(tmp_path / "reviewer.pdf", case, analysis, 2)

    assert captured == {
        "review_id": review.id,
        "doctor_name": "Admin A",
    }


def test_report_metadata_is_not_visible_before_pdf_publication(
    app, users, case_graph, monkeypatch
):
    publication_started = Event()
    allow_publication = Event()
    real_replace = os.replace
    real_link = os.link

    def pause_before(real_publish):
        def publish(*args, **kwargs):
            publication_started.set()
            assert allow_publication.wait(timeout=5)
            return real_publish(*args, **kwargs)

        return publish

    monkeypatch.setattr(os, "replace", pause_before(real_replace))
    monkeypatch.setattr(os, "link", pause_before(real_link))
    monkeypatch.setattr(
        ReportService,
        "_build_pdf",
        lambda _service, path, _case, _analysis, version: Path(path).write_bytes(
            f"report version {version}".encode()
        ),
    )

    def generate_once():
        with app.app_context():
            case = db.session.get(Case, case_graph["own"]["case_id"])
            analysis = db.session.get(
                Analysis, case_graph["own"]["analysis_id"]
            )
            doctor = db.session.get(User, users["doctor"])
            try:
                return ReportService(app).generate(case, analysis, doctor).id
            finally:
                db.session.remove()

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(generate_once)
        assert publication_started.wait(timeout=5)
        with app.app_context():
            visible_report = db.session.scalar(
                db.select(Report).where(
                    Report.case_id == case_graph["own"]["case_id"],
                    Report.report_version == 2,
                )
            )
            db.session.remove()
        allow_publication.set()
        report_id = future.result(timeout=5)

    assert visible_report is None
    with app.app_context():
        report = db.session.get(Report, report_id)
        assert (Path(app.config["REPORT_FOLDER"]) / report.pdf_path).is_file()
