from typing import Literal

from pydantic import SecretStr
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    app_name: str = "Portfolio API"
    app_environment: Literal[
        "development",
        "test",
        "production",
    ] = "development"
    debug: bool = False

    db_user: str
    db_password: SecretStr
    db_host: str
    db_port: int = 5432
    db_name: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
