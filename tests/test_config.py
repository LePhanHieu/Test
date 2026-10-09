import pytest

from skin_cancer.webapp.config import database_config


def test_upload_and_rate_limit_defaults_are_consistent(monkeypatch):
    for name in (
        "RATELIMIT_LOGIN",
        "RATELIMIT_REPORT",
        "RATELIMIT_EXPENSIVE",
        "RATELIMIT_STORAGE_URI",
    ):
        monkeypatch.delenv(name, raising=False)

    config = database_config()

    assert config["BATCH_MAX_IMAGES"] == 20
    assert config["BATCH_MAX_FILE_BYTES"] == 10 * 1024 * 1024
    assert config["MAX_CONTENT_LENGTH"] > (
        config["BATCH_MAX_IMAGES"] * config["BATCH_MAX_FILE_BYTES"]
    )
    assert config["BATCH_MAX_IMAGE_PIXELS"] == 25_000_000
    assert config["RATELIMIT_STORAGE_URI"] == "memory://"
    assert config["RATELIMIT_LOGIN"] == "5 per minute"


def test_tls_and_ssl_cannot_both_be_enabled(monkeypatch):
    monkeypatch.setenv("MAIL_USE_TLS", "true")
    monkeypatch.setenv("MAIL_USE_SSL", "true")

    with pytest.raises(RuntimeError, match="không được cùng bằng true"):
        database_config()


def test_secure_cookie_and_rate_limit_environment_values(monkeypatch):
    monkeypatch.setenv("MAIL_USE_TLS", "false")
    monkeypatch.setenv("MAIL_USE_SSL", "true")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    monkeypatch.setenv("RATELIMIT_STORAGE_URI", "redis://cache:6379/1")
    monkeypatch.setenv("RATELIMIT_REPORT", "9 per hour")

    config = database_config()

    assert config["MAIL_USE_SSL"] is True
    assert config["SESSION_COOKIE_SECURE"] is True
    assert config["RATELIMIT_STORAGE_URI"] == "redis://cache:6379/1"
    assert config["RATELIMIT_REPORT"] == "9 per hour"
