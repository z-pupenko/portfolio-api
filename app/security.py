from datetime import UTC, datetime, timedelta

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from app.config import settings

password_hasher = PasswordHash.recommended()


class InvalidAccessTokenError(ValueError):
    """Raised when an access token cannot identify a valid user."""


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(
    password: str,
    password_hash: str,
) -> bool:
    try:
        return password_hasher.verify(
            password,
            password_hash,
        )
    except UnknownHashError:
        return False


def create_access_token(user_id: int) -> str:
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes,
    )

    payload = {
        "sub": str(user_id),
        "exp": expires_at,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
    except InvalidTokenError as error:
        raise InvalidAccessTokenError("Invalid or expired access token.") from error

    subject = payload.get("sub")

    try:
        user_id = int(subject)
    except (TypeError, ValueError) as error:
        raise InvalidAccessTokenError("Access token has no valid subject.") from error

    if user_id <= 0:
        raise InvalidAccessTokenError("Access token has no valid subject.")

    return user_id
