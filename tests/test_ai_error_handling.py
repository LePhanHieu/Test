import ast
import importlib.util
from pathlib import Path

from skin_cancer.webapp.extensions import db
from skin_cancer.webapp.models import Analysis, CaseImage


APP_PATH = Path("skin_cancer/webapp/app.py")


def _analyze_function():
    tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
    return next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "analyze_case_image"
    )


def test_analysis_is_committed_before_inference_starts():
    function = _analyze_function()
    calls = [node for node in ast.walk(function) if isinstance(node, ast.Call)]

    inference_line = min(
        node.lineno
        for node in calls
        if isinstance(node.func, ast.Name) and node.func.id == "run_ai_inference"
    )
    commit_line = min(
        node.lineno
        for node in calls
        if isinstance(node.func, ast.Attribute)
        and node.func.attr == "commit"
        and isinstance(node.func.value, ast.Attribute)
        and node.func.value.attr == "session"
    )

    assert commit_line < inference_line


def test_analysis_id_exists_if_initial_database_flush_fails():
    function = _analyze_function()
    outer_try = next(node for node in function.body if isinstance(node, ast.Try))
    assignment = next(
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "analysis_id"
            for target in node.targets
        )
    )
    assert assignment.lineno < outer_try.lineno


def test_ai_error_response_does_not_expose_exception_detail():
    source = APP_PATH.read_text(encoding="utf-8")
    assert '"detail":\n                    str(exc)' not in source
    assert "mark_analysis_failed(" in source


def test_ai_error_handler_passes_scalar_case_image_id():
    function = _analyze_function()
    handler = next(
        handler
        for node in function.body
        if isinstance(node, ast.Try)
        for handler in node.handlers
        if isinstance(handler.type, ast.Name) and handler.type.id == "Exception"
    )
    call = next(
        node
        for node in ast.walk(handler)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "mark_analysis_failed"
    )

    assert isinstance(call.args[1], ast.Name)
    assert call.args[1].id == "case_image_id"


def test_mark_analysis_failed_persists_audit_state(app, users, case_graph):
    spec = importlib.util.find_spec("skin_cancer.webapp.services.ai_analysis")
    assert spec is not None

    from skin_cancer.webapp.services.ai_analysis import mark_analysis_failed

    with app.app_context():
        analysis = db.session.get(Analysis, case_graph["own"]["analysis_id"])
        image = db.session.get(CaseImage, case_graph["own"]["image_id"])
        analysis.status = "PROCESSING"
        image.status = "PROCESSING"
        db.session.commit()

        mark_analysis_failed(analysis.id, image.id, RuntimeError("private path"))

        db.session.expire_all()
        analysis = db.session.get(Analysis, analysis.id)
        image = db.session.get(CaseImage, image.id)
        assert analysis.status == "FAILED"
        assert analysis.completed_at is not None
        assert analysis.error_message == "RuntimeError: private path"
        assert image.status == "UPLOADED"
