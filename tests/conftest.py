from __future__ import annotations

from pathlib import Path

import pytest

from skin_cancer.webapp.database_app import create_app
from skin_cancer.webapp.extensions import db
from skin_cancer.webapp.models import (
    Analysis,
    Case,
    CaseImage,
    Report,
    UploadBatch,
    User,
)
from skin_cancer.webapp.models.base import utcnow


PASSWORD = "correct horse battery"


@pytest.fixture()
def app(tmp_path):
    instance = tmp_path / "instance"
    application = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
            "WTF_CSRF_ENABLED": True,
            "UPLOAD_FOLDER": str(instance / "uploads"),
            "REPORT_FOLDER": str(instance / "reports"),
            "MEASUREMENT_FOLDER": str(instance / "measurements"),
            "ALLOW_DEMO_SEED": False,
        }
    )

    with application.app_context():
        db.create_all()

    yield application

    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def create_user(*, email: str, role: str, full_name: str) -> User:
    user = User(email=email, role=role, full_name=full_name)
    user.set_password(PASSWORD)
    db.session.add(user)
    return user


@pytest.fixture()
def users(app):
    with app.app_context():
        records = {
            "admin": create_user(
                email="admin@example.test", role="ADMIN", full_name="Admin A"
            ),
            "doctor": create_user(
                email="doctor@example.test", role="DOCTOR", full_name="Doctor A"
            ),
            "other_doctor": create_user(
                email="doctor2@example.test", role="DOCTOR", full_name="Doctor B"
            ),
            "patient": create_user(
                email="patient@example.test", role="USER", full_name="Patient A"
            ),
            "other_patient": create_user(
                email="patient2@example.test", role="USER", full_name="Patient B"
            ),
        }
        db.session.commit()
        ids = {name: user.id for name, user in records.items()}

    return ids


@pytest.fixture()
def case_graph(app, users):
    with app.app_context():
        own_case = Case(
            case_code="CASE-OWN",
            patient_user_id=users["patient"],
            doctor_id=users["doctor"],
            status="ANALYZED",
        )
        other_case = Case(
            case_code="CASE-OTHER",
            patient_user_id=users["other_patient"],
            doctor_id=users["other_doctor"],
            status="ANALYZED",
        )
        temporary_case = Case(
            case_code="CASE-TEMP",
            patient_snapshot={
                "full_name": "Temporary Patient",
                "email": "temporary@example.test",
            },
            doctor_id=users["doctor"],
        )
        db.session.add_all([own_case, other_case, temporary_case])
        db.session.flush()

        objects = {}
        for label, case, doctor_id in (
            ("own", own_case, users["doctor"]),
            ("other", other_case, users["other_doctor"]),
        ):
            batch = UploadBatch(
                case_id=case.id,
                doctor_id=doctor_id,
                total_images=1,
                success_count=1,
                status="COMPLETED",
                completed_at=utcnow(),
            )
            db.session.add(batch)
            db.session.flush()
            image = CaseImage(
                case_id=case.id,
                batch_id=batch.id,
                image_path=f"/tmp/{label}.jpg",
                original_filename=f"{label}.jpg",
                mime_type="image/jpeg",
                file_size=4,
                uploaded_by=doctor_id,
                status="COMPLETED",
            )
            db.session.add(image)
            db.session.flush()
            analysis = Analysis(
                case_id=case.id,
                case_image_id=image.id,
                status="COMPLETED",
            )
            db.session.add(analysis)
            db.session.flush()
            report = Report(
                case_id=case.id,
                analysis_id=analysis.id,
                pdf_path=f"{case.case_code}/report_v1.pdf",
                generated_by=doctor_id,
                report_version=1,
            )
            db.session.add(report)
            db.session.flush()
            objects[label] = {
                "case_id": case.id,
                "batch_id": batch.id,
                "image_id": image.id,
                "analysis_id": analysis.id,
                "report_id": report.id,
            }

        db.session.commit()
        report_root = Path(app.config["REPORT_FOLDER"])
        for label in ("own", "other"):
            record = db.session.get(Report, objects[label]["report_id"])
            report_path = report_root / record.pdf_path
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_bytes(b"%PDF-1.4\n%%EOF")

        return {
            **objects,
            "temporary_case_id": temporary_case.id,
        }


@pytest.fixture()
def login(client, users):
    def perform(role_name: str):
        token = client.get("/api/auth/csrf").get_json()["csrf_token"]
        response = client.post(
            "/api/auth/login",
            json={
                "email": f"{role_name if role_name != 'other_doctor' else 'doctor2'}@example.test",
                "password": PASSWORD,
            },
            headers={"X-CSRFToken": token},
        )
        assert response.status_code == 200
        return response

    return perform
