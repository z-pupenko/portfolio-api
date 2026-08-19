from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.config import settings
from app.security import (
    InvalidAccessTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_does_not_return_plain_password():
    password = "secure-password"
    result = hash_password(password)

    assert result != password


def test_verify_password_accepts_correct_password():
    password = "secure-password"
    result = hash_password(password)

    assert verify_password(password, result) is True


def test_verify_password_rejects_wrong_or_unknown_hash():
    password = "secure-password"
    password_hash = hash_password(password)

    assert verify_password("other-password", password_hash) is False
    assert verify_password(password, "!legacy-account-disabled") is False


def test_access_token_round_trip_returns_user_id():
    token = create_access_token(user_id=42)

    assert decode_access_token(token) == 42


def test_decode_access_token_rejects_invalid_token():
    with pytest.raises(InvalidAccessTokenError):
        decode_access_token("not-a-jwt")


def test_decode_access_token_rejects_expired_token():
    token = jwt.encode(
        {
            "sub": "42",
            "exp": datetime.now(UTC) - timedelta(seconds=1),
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token)
