import ast
from pathlib import Path


APP_PATH = Path("skin_cancer/webapp/app.py")


def load_current_interpretation():
    tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "CLASS_INFO"
            for target in node.targets
        ):
            selected.append(node)
        if isinstance(node, ast.FunctionDef) and node.name == "generate_interpretation":
            selected.append(node)
    namespace = {}
    exec(compile(ast.Module(body=selected, type_ignores=[]), APP_PATH, "exec"), namespace)
    return namespace["generate_interpretation"]


def test_multiclass_summary_uses_the_predicted_class_probability():
    generate_interpretation = load_current_interpretation()

    interpretation = generate_interpretation(
        0.99,
        "NV",
        {"NV": 0.30, "MEL": 0.70},
    )

    assert "30% khả năng là Nốt ruồi" in interpretation["summary"]
    assert "99% khả năng là Nốt ruồi" not in interpretation["summary"]
