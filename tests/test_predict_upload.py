import ast
import importlib.util
from io import BytesIO
from pathlib import Path

import pytest


APP_PATH = Path("skin_cancer/webapp/app.py")


def test_limited_upload_reader_rejects_content_above_the_byte_limit():
    spec = importlib.util.find_spec("skin_cancer.webapp.services.image_upload")
    assert spec is not None

    from skin_cancer.webapp.services.image_upload import (
        UploadTooLarge,
        read_limited_upload,
    )

    limit = 10 * 1024 * 1024
    stream = BytesIO(b"x" * (limit + 1))
    with pytest.raises(UploadTooLarge):
        read_limited_upload(stream, limit)


def test_predict_uses_the_limited_upload_reader_before_image_decode():
    tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "predict"
    )
    calls = [node for node in ast.walk(function) if isinstance(node, ast.Call)]
    limited_read_line = min(
        node.lineno
        for node in calls
        if isinstance(node.func, ast.Name) and node.func.id == "read_limited_upload"
    )
    image_open_line = min(
        node.lineno
        for node in calls
        if isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "Image"
        and node.func.attr == "open"
    )

    assert limited_read_line < image_open_line
