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


def test_settings_rejects_debug_mode_in_production():
    with pytest.raises(
        ValidationError,
        match="Debug mode must be disabled in production",
    ):
        Settings(
            app_environment="production",
            debug=True,
            db_user="test_user",
            db_password="test_password",
            db_host="localhost",
            db_name="test_database",
            jwt_secret_key="x" * 32,
            _env_file=None,
        )


def test_settings_rejects_short_jwt_secret_in_production():
    with pytest.raises(
        ValidationError,
        match="JWT secret key must contain at least 32 characters in production",
    ):
        Settings(
            app_environment="production",
            debug=False,
            db_user="test_user",
            db_password="test_password",
            db_host="localhost",
            db_name="test_database",
            jwt_secret_key="too-short",
            _env_file=None,
        )


def test_settings_accepts_valid_production_configuration():
    settings = Settings(
        app_environment="production",
        debug=False,
        db_user="test_user",
        db_password="test_password",
        db_host="localhost",
        db_name="test_database",
        jwt_secret_key="x" * 32,
        _env_file=None,
    )

    assert settings.app_environment == "production"
    assert settings.debug is False


def test_development_allows_debug_and_short_jwt_secret():
    settings = Settings(
        app_environment="development",
        debug=True,
        db_user="test_user",
        db_password="test_password",
        db_host="localhost",
        db_name="test_database",
        jwt_secret_key="test-secret",
        _env_file=None,
    )

    assert settings.debug is True


def test_settings_validation_errors_hide_secret_inputs():
    database_password = "sensitive-database-password"
    jwt_secret = "sensitive-production-jwt-secret-key"

    with pytest.raises(ValidationError) as error:
        Settings(
            app_environment="production",
            debug=True,
            db_user="test_user",
            db_password=database_password,
            db_host="localhost",
            db_name="test_database",
            jwt_secret_key=jwt_secret,
            _env_file=None,
        )

    error_message = str(error.value)
    assert database_password not in error_message
    assert jwt_secret not in error_message
