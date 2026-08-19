import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
    )

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    TestSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    def override_get_db():
        db = TestSessionLocal()

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    credentials = {
        "email": "api-user@example.com",
        "password": "secure-password",
        "full_name": "API User",
    }

    registration_response = client.post(
        "/auth/register",
        json=credentials,
    )
    assert registration_response.status_code == 201

    token_response = client.post(
        "/auth/token",
        data={
            "username": credentials["email"],
            "password": credentials["password"],
        },
    )
    assert token_response.status_code == 200

    access_token = token_response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}
