from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
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
    log_level: Literal[
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ] = "INFO"

    db_user: str
    db_password: SecretStr
    db_host: str
    db_port: int = 5432
    db_name: str

    jwt_secret_key: SecretStr
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=30, gt=0)

    @model_validator(mode="after")
    def validate_production_settings(self) -> Self:
        if self.app_environment == "production" and self.debug:
            raise ValueError("Debug mode must be disabled in production")
        if self.app_environment == "production":
            jwt_secret = self.jwt_secret_key.get_secret_value()

            if len(jwt_secret) < 32:
                raise ValueError(
                    "JWT secret key must contain at least 32 characters in production"
                )

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
