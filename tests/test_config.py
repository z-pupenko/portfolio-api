import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_uses_default_database_port():
    settings = Settings(
        db_user="test_user",
        db_password="test_password",
        db_host="localhost",
        db_name="test_database",
        _env_file=None,
        jwt_secret_key="test-secret",
    )

    assert settings.db_port == 5432


def test_settings_rejects_invalid_database_port():
    with pytest.raises(ValidationError):
        Settings(
            db_user="test_user",
            db_password="test_password",
            db_host="localhost",
            db_port="not-a-number",
            db_name="test_database",
            _env_file=None,
            jwt_secret_key="test-secret",
        )


def test_settings_rejects_non_positive_token_expiry():
    with pytest.raises(ValidationError):
        Settings(
            db_user="test_user",
            db_password="test_password",
            db_host="localhost",
            db_name="test_database",
            jwt_secret_key="test-secret",
            access_token_expire_minutes=0,
            _env_file=None,
        )


def test_settings_uses_default_log_level():
    settings = Settings(
        db_user="test_user",
        db_password="test_password",
        db_host="localhost",
        db_name="test_database",
        jwt_secret_key="test-secret",
        _env_file=None,
    )

    assert settings.log_level == "INFO"


def test_settings_rejects_invalid_log_level():
    with pytest.raises(ValidationError):
        Settings(
            db_user="test_user",
            db_password="test_password",
            db_host="localhost",
            db_name="test_database",
            jwt_secret_key="test-secret",
            log_level="VERBOSE",
            _env_file=None,
        )
