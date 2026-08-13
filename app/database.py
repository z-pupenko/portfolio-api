from collections.abc import Generator

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Session,
    sessionmaker,
)

from app.config import settings

# --------------------------------------------------
# Database engine
# --------------------------------------------------

database_url = URL.create(
    drivername="postgresql+psycopg",
    username=settings.db_user,
    password=settings.db_password.get_secret_value(),
    host=settings.db_host,
    port=settings.db_port,
    database=settings.db_name,
)


engine = create_engine(database_url)


# --------------------------------------------------
# Session factory
# --------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


# --------------------------------------------------
# Declarative base
# --------------------------------------------------


class Base(DeclarativeBase):
    pass


# --------------------------------------------------
# FastAPI dependency
# --------------------------------------------------


def get_db() -> Generator[Session]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
