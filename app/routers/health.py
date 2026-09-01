from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db


router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get("/live")
def get_liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def get_readiness(
    db: Session = Depends(get_db),
) -> dict[str, str]:
    try:
        db.execute(select(1))
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        ) from error

    return {"status": "ok"}
