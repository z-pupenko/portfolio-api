from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.schemas import UserCreate
from app.security import hash_password, verify_password


class EmailAlreadyRegisteredError(ValueError):
    """Raised when an email already belongs to a user."""


class InvalidCredentialsError(ValueError):
    """Raised when login credentials are invalid."""


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(
    db: Session,
    email: str,
) -> User | None:
    normalized_email = normalize_email(email)
    statement = select(User).where(
        User.email == normalized_email,
    )

    return db.scalar(statement)


def create_user(
    db: Session,
    user_data: UserCreate,
) -> User:
    normalized_email = normalize_email(user_data.email)

    existing_user = get_user_by_email(
        db,
        normalized_email,
    )

    if existing_user is not None:
        raise EmailAlreadyRegisteredError("A user with this email already exists.")

    user = User(
        email=normalized_email,
        full_name=user_data.full_name,
        password_hash=hash_password(user_data.password),
    )

    db.add(user)
    db.flush()

    return user


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User:
    user = get_user_by_email(db, email)

    if user is None or not verify_password(
        password,
        user.password_hash,
    ):
        raise InvalidCredentialsError("Incorrect email or password.")

    return user
