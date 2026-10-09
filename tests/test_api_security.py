import csv
import ast
from pathlib import Path

import pytest

from skin_cancer.webapp.services.batch_upload import BatchUploadService, CSV_COLUMNS


@pytest.mark.parametrize("prefix", ["=", "+", "-", "@", "\t", "\r"])
def test_csv_export_neutralizes_spreadsheet_formula_prefixes(tmp_path, prefix):
    path = tmp_path / "batch.csv"
    row = {column: "" for column in CSV_COLUMNS}
    row.update(filename=f"{prefix}payload.jpg", status="FAILED")

    BatchUploadService.write_csv([row], path)

    with path.open(newline="", encoding="utf-8") as handle:
        exported = next(csv.DictReader(handle))
    assert exported["filename"].startswith("'")
    assert exported["filename"][1:] == row["filename"]


@pytest.mark.parametrize(
    ("body", "content_type"),
    [
        ("[]", "application/json"),
        ('"analysis"', "application/json"),
        ("7", "application/json"),
        ("null", "application/json"),
    ],
)
def test_report_generation_rejects_non_object_json_as_json(
    client, users, case_graph, login, body, content_type
):
    login("doctor")
    token = client.get("/api/auth/csrf").get_json()["csrf_token"]
    response = client.post(
        f"/api/cases/{case_graph['own']['case_id']}/reports",
        data=body,
        content_type=content_type,
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 400
    assert response.is_json
    assert response.get_json()["success"] is False


def test_repeated_failed_logins_are_rate_limited(app, client, users):
    app.config["RATELIMIT_LOGIN"] = "2 per minute"
    token = client.get("/api/auth/csrf").get_json()["csrf_token"]
    headers = {"X-CSRFToken": token}
    credentials = {
        "email": "patient@example.test",
        "password": "incorrect password",
    }

    assert client.post("/api/auth/login", json=credentials, headers=headers).status_code == 401
    assert client.post("/api/auth/login", json=credentials, headers=headers).status_code == 401
    response = client.post("/api/auth/login", json=credentials, headers=headers)
    assert response.status_code == 429
    assert response.is_json


def test_repeated_report_requests_are_rate_limited(
    app, client, users, case_graph, login
):
    app.config["RATELIMIT_REPORT"] = "1 per minute"
    login("doctor")
    token = client.get("/api/auth/csrf").get_json()["csrf_token"]
    headers = {"X-CSRFToken": token}
    url = f"/api/cases/{case_graph['own']['case_id']}/reports"

    first = client.post(url, json={"analysis_id": 999999}, headers=headers)
    second = client.post(url, json={"analysis_id": 999999}, headers=headers)
    assert first.status_code == 404
    assert second.status_code == 429


def test_repeated_upload_requests_are_rate_limited(
    app, client, users, case_graph, login
):
    app.config["RATELIMIT_EXPENSIVE"] = "1 per minute"
    login("doctor")
    token = client.get("/api/auth/csrf").get_json()["csrf_token"]
    headers = {"X-CSRFToken": token}
    url = f"/api/cases/{case_graph['own']['case_id']}/upload-batch"

    first = client.post(url, data={}, headers=headers)
    second = client.post(url, data={}, headers=headers)
    assert first.status_code == 400
    assert second.status_code == 429


def test_ai_compute_routes_declare_rate_limits():
    tree = ast.parse(Path("skin_cancer/webapp/app.py").read_text(encoding="utf-8"))
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }

    for function_name in ("predict", "analyze_case_image"):
        decorators = functions[function_name].decorator_list
        assert any(
            isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Attribute)
            and decorator.func.attr == "limit"
            for decorator in decorators
        )
