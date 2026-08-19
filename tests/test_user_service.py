from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.models import User
from app.schemas import UserCreate
from app.security import hash_password, verify_password
from app.services.users import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    authenticate_user,
    create_user,
)


def test_user_successful_creation():
    db = MagicMock(spec=Session)
    db.scalar.return_value = None

    user_data = UserCreate(
        email="Zakhar@Example.com",
        password="secure-password",
        full_name="Zakhar",
    )

    user = create_user(db, user_data)

    assert user.email == "zakhar@example.com"
    assert user.full_name == "Zakhar"
    assert user.password_hash != "secure-password"
    assert verify_password("secure-password", user.password_hash) is True

    db.add.assert_called_once_with(user)
    db.flush.assert_called_once_with()
    db.commit.assert_not_called()


def test_create_user_rejects_duplicate_email():
    db = MagicMock(spec=Session)

    existing_user = User(
        email="zakhar@example.com",
        password_hash="existing-hash",
    )
    db.scalar.return_value = existing_user

    user_data = UserCreate(
        email="zakhar@example.com",
        password="secure-password",
    )

    with pytest.raises(EmailAlreadyRegisteredError):
        create_user(db, user_data)

    db.add.assert_not_called()
    db.flush.assert_not_called()


def test_authenticate_user_returns_verified_user():
    db = MagicMock(spec=Session)
    user = User(
        email="zakhar@example.com",
        password_hash=hash_password("secure-password"),
    )
    db.scalar.return_value = user

    result = authenticate_user(
        db,
        "ZAKHAR@example.com",
        "secure-password",
    )

    assert result is user


@pytest.mark.parametrize(
    ("stored_user", "password"),
    [
        (None, "secure-password"),
        (
            User(
                email="zakhar@example.com",
                password_hash=hash_password("secure-password"),
            ),
            "wrong-password",
        ),
        (
            User(
                email="legacy-owner@internal.invalid",
                password_hash="!legacy-account-disabled",
            ),
            "secure-password",
        ),
    ],
    ids=["unknown-email", "wrong-password", "disabled-hash"],
)
def test_authenticate_user_rejects_invalid_credentials(
    stored_user: User | None,
    password: str,
):
    db = MagicMock(spec=Session)
    db.scalar.return_value = stored_user

    with pytest.raises(
        InvalidCredentialsError,
        match="Incorrect email or password",
    ):
        authenticate_user(
            db,
            "zakhar@example.com",
            password,
        )
