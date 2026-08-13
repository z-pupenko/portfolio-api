from decimal import Decimal

from fastapi.testclient import TestClient


def test_create_portfolio_through_api(
    client: TestClient,
):
    payload = {
        "name": "Growth",
        "description": "Long-term investments",
        "starting_cash": "10000.00",
        "base_currency": "gbp",
    }

    response = client.post(
        "/portfolios/",
        json=payload,
    )

    assert response.status_code == 201
    response_data = response.json()

    assert response_data["name"] == payload["name"]
    assert response_data["description"] == payload["description"]
    assert response_data["base_currency"] == "GBP"
    assert Decimal(response_data["starting_cash"]) == Decimal(payload["starting_cash"])
    assert isinstance(response_data["id"], int)
    assert response_data["created_at"] is not None
    portfolio_id = response_data["id"]

    get_response = client.get(
        f"/portfolios/{portfolio_id}",
    )

    assert get_response.status_code == 200
    saved_portfolio = get_response.json()

    assert saved_portfolio["id"] == portfolio_id
    assert saved_portfolio["name"] == payload["name"]
