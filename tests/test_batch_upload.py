from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from werkzeug.datastructures import FileStorage

from skin_cancer.webapp.extensions import db
from skin_cancer.webapp.models import Case, UploadBatch, User
from skin_cancer.webapp.services.batch_upload import BatchUploadService


def image_bytes(image_format="PNG", size=(16, 16)):
    output = BytesIO()
    Image.new("RGB", size, "red").save(output, format=image_format)
    return output.getvalue()


def uploaded_file(data, filename, mimetype):
    return FileStorage(
        stream=BytesIO(data),
        filename=filename,
        content_type=mimetype,
    )


def service_for(app, users, case_graph):
    case = db.session.get(Case, case_graph["own"]["case_id"])
    batch = db.session.get(UploadBatch, case_graph["own"]["batch_id"])
    actor = db.session.get(User, users["doctor"])
    return BatchUploadService(app, batch, case, actor)


def test_rejects_image_whose_decoded_format_does_not_match_extension(
    app, users, case_graph
):
    with app.app_context():
        result = service_for(app, users, case_graph).process(
            [uploaded_file(image_bytes("PNG"), "spoof.jpg", "image/jpeg")]
        )
        assert result.items[0]["status"] == "FAILED"
        assert "format" in result.items[0]["error_message"].lower()


def test_rejects_image_over_pixel_budget(app, users, case_graph):
    app.config["BATCH_MAX_IMAGE_PIXELS"] = 100
    with app.app_context():
        result = service_for(app, users, case_graph).process(
            [uploaded_file(image_bytes("PNG", (20, 20)), "large.png", "image/png")]
        )
        assert result.items[0]["status"] == "FAILED"
        assert "pixel" in result.items[0]["error_message"].lower()


def test_accepts_jpeg_bytes_with_jpg_extension(app, users, case_graph):
    with app.app_context():
        result = service_for(app, users, case_graph).process(
            [uploaded_file(image_bytes("JPEG"), "lesion.jpg", "image/jpeg")]
        )
        assert result.items[0]["status"] == "UPLOADED"
        assert result.items[0]["filename"].endswith(".jpg")


def test_enforces_per_file_byte_limit(app, users, case_graph):
    app.config["BATCH_MAX_FILE_BYTES"] = 8
    with app.app_context():
        result = service_for(app, users, case_graph).process(
            [uploaded_file(image_bytes("PNG"), "lesion.png", "image/png")]
        )
        assert result.items[0]["status"] == "FAILED"
        assert "maximum size" in result.items[0]["error_message"]


def test_request_limit_allows_two_six_megabyte_files(app):
    assert app.config["MAX_CONTENT_LENGTH"] > 12 * 1024 * 1024


def test_exception_during_batch_removes_files_created_by_that_batch(
    app, users, case_graph, monkeypatch
):
    real_write_bytes = Path.write_bytes
    write_count = 0

    def fail_second_write(path, data):
        nonlocal write_count
        write_count += 1
        if write_count == 2:
            raise OSError("simulated disk failure")
        return real_write_bytes(path, data)

    monkeypatch.setattr(Path, "write_bytes", fail_second_write)

    with app.app_context():
        service = service_for(app, users, case_graph)
        files = [
            uploaded_file(image_bytes("PNG", (16, 16)), "one.png", "image/png"),
            uploaded_file(image_bytes("PNG", (17, 17)), "two.png", "image/png"),
        ]
        with pytest.raises(OSError, match="simulated disk failure"):
            service.process(files)
        db.session.rollback()

    image_dir = Path(app.config["UPLOAD_FOLDER"]) / "images"
    assert list(image_dir.glob("*")) == []
