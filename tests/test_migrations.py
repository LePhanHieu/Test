from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

from skin_cancer.webapp.config import PROJECT_ROOT
from skin_cancer.webapp.database_app import create_app


def test_fresh_database_upgrades_to_single_head_without_drift(tmp_path):
    database_path = tmp_path / "migrated.db"
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "migration-test-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
            "ALLOW_DEMO_SEED": False,
        }
    )
    runner = app.test_cli_runner()

    upgrade = runner.invoke(args=["db", "upgrade"])
    assert upgrade.exit_code == 0, upgrade.output
    assert database_path.exists()

    alembic_config = Config()
    alembic_config.set_main_option(
        "script_location", str(PROJECT_ROOT / "migrations")
    )
    assert ScriptDirectory.from_config(alembic_config).get_heads() == [
        "9d731c80a1f2"
    ]

    with create_engine(f"sqlite:///{database_path}").connect() as connection:
        current = connection.scalar(text("SELECT version_num FROM alembic_version"))
    assert current == "9d731c80a1f2"

    check = runner.invoke(args=["db", "check"])
    assert check.exit_code == 0, check.output
