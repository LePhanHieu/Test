from pathlib import Path


def test_pdf_export_matches_backend_optional_review_policy():
    source = Path("skin_cancer/webapp/static/js/main.js").read_text(encoding="utf-8")

    assert "hasSavedDoctorDiagnosis" not in source
    assert "Chưa có chẩn đoán của bác sĩ" not in source
