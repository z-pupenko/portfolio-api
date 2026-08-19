from fastapi.testclient import TestClient


def register_and_login(
    client: TestClient,
    email: str,
) -> dict[str, str]:
    password = "secure-password"
    registration_response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": email.split("@", maxsplit=1)[0],
        },
    )
    assert registration_response.status_code == 201

    token_response = client.post(
        "/auth/token",
        data={
            "username": email,
            "password": password,
        },
    )
    assert token_response.status_code == 200

    return {"Authorization": f"Bearer {token_response.json()['access_token']}"}


def create_portfolio(
    client: TestClient,
    headers: dict[str, str],
    name: str,
) -> int:
    response = client.post(
        "/portfolios/",
        headers=headers,
        json={
            "name": name,
            "starting_cash": "10000",
            "base_currency": "GBP",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_users_only_list_their_own_portfolios(
    client: TestClient,
):
    multiple_headers = register_and_login(client, "multiple@example.com")
    single_headers = register_and_login(client, "single@example.com")
    empty_headers = register_and_login(client, "empty@example.com")

    create_portfolio(client, multiple_headers, "Growth")
    create_portfolio(client, multiple_headers, "Retirement")
    create_portfolio(client, single_headers, "Income")

    multiple_response = client.get("/portfolios/", headers=multiple_headers)
    single_response = client.get("/portfolios/", headers=single_headers)
    empty_response = client.get("/portfolios/", headers=empty_headers)

    assert [item["name"] for item in multiple_response.json()] == [
        "Growth",
        "Retirement",
    ]
    assert [item["name"] for item in single_response.json()] == ["Income"]
    assert empty_response.json() == []


def test_user_cannot_access_another_users_portfolio(
    client: TestClient,
):
    owner_headers = register_and_login(client, "owner@example.com")
    other_headers = register_and_login(client, "other@example.com")
    portfolio_id = create_portfolio(client, owner_headers, "Private")

    response = client.get(
        f"/portfolios/{portfolio_id}",
        headers=other_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Portfolio not found"


def test_user_cannot_access_another_users_transaction(
    client: TestClient,
):
    owner_headers = register_and_login(client, "owner@example.com")
    other_headers = register_and_login(client, "other@example.com")
    portfolio_id = create_portfolio(client, owner_headers, "Private")

    asset_response = client.post(
        "/assets/",
        headers=owner_headers,
        json={
            "symbol": "AAPL",
            "name": "Apple",
            "asset_type": "stock",
            "currency": "GBP",
        },
    )
    asset_id = asset_response.json()["id"]

    transaction_response = client.post(
        f"/portfolios/{portfolio_id}/transactions/",
        headers=owner_headers,
        json={
            "asset_id": asset_id,
            "transaction_type": "buy",
            "quantity": "1",
            "price": "100",
            "fees": "0",
            "transaction_date": "2026-08-17",
        },
    )
    assert transaction_response.status_code == 201
    transaction_id = transaction_response.json()["id"]

    direct_response = client.get(
        f"/transactions/{transaction_id}",
        headers=other_headers,
    )
    nested_response = client.get(
        f"/portfolios/{portfolio_id}/transactions/",
        headers=other_headers,
    )

    assert direct_response.status_code == 404
    assert direct_response.json()["detail"] == "Transaction not found"
    assert nested_response.status_code == 404
    assert nested_response.json()["detail"] == "Portfolio not found"
