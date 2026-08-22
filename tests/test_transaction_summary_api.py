from decimal import Decimal

from fastapi.testclient import TestClient


def create_portfolio(
    client: TestClient,
    headers: dict[str, str],
    name: str = "Analytics",
) -> int:
    response = client.post(
        "/portfolios/",
        headers=headers,
        json={
            "name": name,
            "starting_cash": "10000",
            "base_currency": "USD",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_asset(
    client: TestClient,
    headers: dict[str, str],
) -> int:
    response = client.post(
        "/assets/",
        headers=headers,
        json={
            "symbol": "AAPL",
            "name": "Apple",
            "asset_type": "stock",
            "currency": "USD",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_transaction(
    client: TestClient,
    headers: dict[str, str],
    portfolio_id: int,
    asset_id: int,
    transaction_type: str,
    quantity: str,
    price: str,
    fees: str,
    transaction_date: str,
) -> None:
    response = client.post(
        f"/portfolios/{portfolio_id}/transactions/",
        headers=headers,
        json={
            "asset_id": asset_id,
            "transaction_type": transaction_type,
            "quantity": quantity,
            "price": price,
            "fees": fees,
            "transaction_date": transaction_date,
        },
    )
    assert response.status_code == 201


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
            "full_name": "Summary User",
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


def test_transaction_summary_filters_and_aggregates_rows(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    portfolio_id = create_portfolio(client, auth_headers)
    asset_id = create_asset(client, auth_headers)

    transactions = [
        ("buy", "1", "90", "1.00", "2025-12-15"),
        ("buy", "5", "100", "1.50", "2026-01-10"),
        ("sell", "2", "120", "2.00", "2026-02-10"),
    ]
    for transaction_type, quantity, price, fees, transaction_date in transactions:
        create_transaction(
            client,
            auth_headers,
            portfolio_id,
            asset_id,
            transaction_type,
            quantity,
            price,
            fees,
            transaction_date,
        )

    response = client.get(
        f"/portfolios/{portfolio_id}/transaction-summary",
        headers=auth_headers,
        params={
            "start_date": "2026-01-01",
            "end_date": "2026-06-30",
        },
    )

    assert response.status_code == 200
    response_data = response.json()
    assert response_data["portfolio_id"] == portfolio_id
    assert response_data["start_date"] == "2026-01-01"
    assert response_data["end_date"] == "2026-06-30"
    assert response_data["transaction_count"] == 2

    asset_summary = response_data["breakdown"]["by_asset"][0]
    assert asset_summary["symbol"] == "AAPL"
    assert Decimal(asset_summary["total_bought"]) == Decimal("5")
    assert Decimal(asset_summary["total_sold"]) == Decimal("2")
    assert Decimal(asset_summary["net_quantity"]) == Decimal("3")
    assert Decimal(asset_summary["gross_traded_value"]) == Decimal("740")
    assert Decimal(asset_summary["total_fees"]) == Decimal("3.50")

    currency_summary = response_data["breakdown"]["by_currency"][0]
    assert currency_summary["currency"] == "USD"
    assert currency_summary["transaction_count"] == 2
    assert Decimal(currency_summary["gross_traded_value"]) == Decimal("740")
    assert Decimal(currency_summary["total_fees"]) == Decimal("3.50")


def test_transaction_summary_returns_empty_report(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    portfolio_id = create_portfolio(client, auth_headers)

    response = client.get(
        f"/portfolios/{portfolio_id}/transaction-summary",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "portfolio_id": portfolio_id,
        "start_date": None,
        "end_date": None,
        "transaction_count": 0,
        "breakdown": {
            "by_asset": [],
            "by_currency": [],
        },
    }


def test_transaction_summary_rejects_backwards_date_range(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    portfolio_id = create_portfolio(client, auth_headers)

    response = client.get(
        f"/portfolios/{portfolio_id}/transaction-summary",
        headers=auth_headers,
        params={
            "start_date": "2026-08-01",
            "end_date": "2026-01-01",
        },
    )

    assert response.status_code == 422
    assert "start_date must be on or before end_date" in response.text


def test_transaction_summary_hides_another_users_portfolio(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    portfolio_id = create_portfolio(client, auth_headers, name="Private")
    other_headers = register_and_login(client, "summary-other@example.com")

    response = client.get(
        f"/portfolios/{portfolio_id}/transaction-summary",
        headers=other_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Portfolio not found"
