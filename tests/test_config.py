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
        )
