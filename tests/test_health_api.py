from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app


def test_liveness_returns_ok(client: TestClient):
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_returns_ok_when_database_is_available(
    client: TestClient,
):
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_returns_503_when_database_is_unavailable(
    client: TestClient,
):
    failing_db = MagicMock(spec=Session)
    failing_db.execute.side_effect = SQLAlchemyError("Database connection failed")

    def override_get_db():
        yield failing_db

    app.dependency_overrides[get_db] = override_get_db

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database is unavailable"}
