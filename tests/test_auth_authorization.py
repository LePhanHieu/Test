from skin_cancer.webapp.extensions import db
from skin_cancer.webapp.models import Case, User


def test_passwords_use_scrypt_and_verify(app, users):
    with app.app_context():
        user = db.session.get(User, users["patient"])
        assert user.password_hash.startswith("scrypt:")
        assert user.check_password("correct horse battery") is True
        assert user.check_password("wrong password") is False


def test_login_and_logout_require_csrf(client, users):
    credentials = {
        "email": "patient@example.test",
        "password": "correct horse battery",
    }
    assert client.post("/api/auth/login", json=credentials).status_code == 400

    token = client.get("/api/auth/csrf").get_json()["csrf_token"]
    assert client.post(
        "/api/auth/login", json=credentials, headers={"X-CSRFToken": token}
    ).status_code == 200
    assert client.post("/api/auth/logout").status_code == 400


def test_user_cannot_read_another_users_case_or_report(client, users, case_graph, login):
    login("patient")
    assert client.get(f"/api/cases/{case_graph['own']['case_id']}").status_code == 200
    assert client.get(f"/api/cases/{case_graph['other']['case_id']}").status_code == 404
    assert client.get(
        f"/api/reports/{case_graph['other']['report_id']}/download"
    ).status_code == 404


def test_doctor_cannot_read_another_doctors_case(client, users, case_graph, login):
    login("doctor")
    assert client.get(f"/api/cases/{case_graph['own']['case_id']}").status_code == 200
    assert client.get(f"/api/cases/{case_graph['other']['case_id']}").status_code == 404
    assert client.get(
        f"/api/upload-batches/{case_graph['other']['batch_id']}/csv"
    ).status_code == 404
    assert client.get(
        f"/api/upload-batches/{case_graph['other']['batch_id']}/analysis.csv"
    ).status_code == 404


def test_patient_cannot_download_batch_analysis_csv(client, users, case_graph, login):
    login("patient")
    response = client.get(
        f"/api/upload-batches/{case_graph['own']['batch_id']}/analysis.csv"
    )
    assert response.status_code == 403


def test_temporary_patient_snapshot_does_not_grant_user_access(
    app, client, users, case_graph, login
):
    with app.app_context():
        case = db.session.get(Case, case_graph["temporary_case_id"])
        assert case.patient_user_id is None
        assert case.patient_snapshot["full_name"] == "Temporary Patient"

    login("patient")
    response = client.get(f"/api/cases/{case_graph['temporary_case_id']}")
    assert response.status_code == 404


def test_http_errors_are_json(client):
    response = client.get("/api/cases/999999")
    assert response.status_code == 401
    assert response.is_json
    assert response.get_json()["success"] is False
