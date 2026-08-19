from fastapi.testclient import TestClient

from app.security import decode_access_token


def test_register_user_through_api(
    client: TestClient,
):
    payload = {
        "email": "Zakhar@Example.com",
        "password": "secure-password",
        "full_name": "Zakhar",
    }

    response = client.post(
        "/auth/register",
        json=payload,
    )

    assert response.status_code == 201

    response_data = response.json()

    assert response_data["email"] == "zakhar@example.com"
    assert response_data["full_name"] == payload["full_name"]
    assert isinstance(response_data["id"], int)
    assert response_data["created_at"] is not None
    assert "password" not in response_data
    assert "password_hash" not in response_data


def test_register_user_rejects_duplicate_email(
    client: TestClient,
):
    first_payload = {
        "email": "zakhar@example.com",
        "password": "secure-password",
        "full_name": "Zakhar",
    }

    duplicate_payload = {
        "email": "ZAKHAR@example.com",
        "password": "different-password",
        "full_name": "Someone Else",
    }

    first_response = client.post(
        "/auth/register",
        json=first_payload,
    )
    duplicate_response = client.post(
        "/auth/register",
        json=duplicate_payload,
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["detail"] == (
        "A user with this email already exists."
    )


def test_login_returns_bearer_access_token(
    client: TestClient,
):
    registration_response = client.post(
        "/auth/register",
        json={
            "email": "zakhar@example.com",
            "password": "secure-password",
            "full_name": "Zakhar",
        },
    )
    user_id = registration_response.json()["id"]

    response = client.post(
        "/auth/token",
        data={
            "username": "ZAKHAR@example.com",
            "password": "secure-password",
        },
    )

    assert response.status_code == 200
    response_data = response.json()

    assert response_data["token_type"] == "bearer"
    assert isinstance(response_data["access_token"], str)

    assert decode_access_token(response_data["access_token"]) == user_id


def test_login_rejects_invalid_credentials(
    client: TestClient,
):
    response = client.post(
        "/auth/token",
        data={
            "username": "missing@example.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["detail"] == "Incorrect email or password."


def test_protected_endpoint_requires_access_token(
    client: TestClient,
):
    response = client.get("/portfolios/")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
