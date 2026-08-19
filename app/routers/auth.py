from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import TokenResponse, UserCreate, UserResponse
from app.security import create_access_token
from app.services.users import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    authenticate_user,
    create_user,
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
) -> User:
    try:
        user = create_user(db, user_data)
        db.commit()
    except EmailAlreadyRegisteredError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        ) from error

    db.refresh(user)
    return user


@router.post(
    "/token",
    response_model=TokenResponse,
)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        user = authenticate_user(
            db,
            form_data.username,
            form_data.password,
        )
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    return TokenResponse(
        access_token=create_access_token(user.id),
    )
