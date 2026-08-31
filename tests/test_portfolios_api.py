from decimal import Decimal

from fastapi.testclient import TestClient


def test_create_portfolio_through_api(
    client: TestClient,
    auth_headers: dict[str, str],
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
        headers=auth_headers,
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
        headers=auth_headers,
    )

    assert get_response.status_code == 200
    saved_portfolio = get_response.json()

    assert saved_portfolio["id"] == portfolio_id
    assert saved_portfolio["name"] == payload["name"]


def test_patch_portfolio_rejects_null_starting_cash(
    client: TestClient,
    auth_headers: dict[str, str],
):
    portfolio = {
        "name": "Growth",
        "description": "Long-term investments",
        "starting_cash": "1000",
        "base_currency": "gbp",
    }

    post_response = client.post(
        "/portfolios/",
        json=portfolio,
        headers=auth_headers,
    )

    assert post_response.status_code == 201
    portfolio_id = post_response.json()["id"]
    portfolio_url = f"/portfolios/{portfolio_id}"

    patch_response = client.patch(
        portfolio_url,
        json={"starting_cash": None},
        headers=auth_headers,
    )

    assert patch_response.status_code == 422

    get_response = client.get(
        portfolio_url,
        headers=auth_headers,
    )
    assert get_response.status_code == 200

    saved_portfolio = get_response.json()

    assert Decimal(saved_portfolio["starting_cash"]) == Decimal("1000")
