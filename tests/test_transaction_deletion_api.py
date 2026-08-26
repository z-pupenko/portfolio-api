from fastapi.testclient import TestClient


def test_delete_rejects_buy_required_by_later_sell(
    client: TestClient,
    auth_headers: dict[str, str],
):
    portfolio_response = client.post(
        "/portfolios/",
        headers=auth_headers,
        json={
            "name": "Deletion API",
            "starting_cash": "1000",
            "base_currency": "GBP",
        },
    )
    assert portfolio_response.status_code == 201
    portfolio_id = portfolio_response.json()["id"]

    asset_response = client.post(
        "/assets/",
        headers=auth_headers,
        json={
            "symbol": "DELAPI",
            "name": "Deletion API Asset",
            "asset_type": "stock",
            "currency": "GBP",
        },
    )
    assert asset_response.status_code == 201
    asset_id = asset_response.json()["id"]

    buy_response = client.post(
        f"/portfolios/{portfolio_id}/transactions/",
        headers=auth_headers,
        json={
            "asset_id": asset_id,
            "transaction_type": "buy",
            "quantity": "10",
            "price": "10",
            "fees": "0",
            "transaction_date": "2026-08-01",
        },
    )
    assert buy_response.status_code == 201
    buy_id = buy_response.json()["id"]

    sell_response = client.post(
        f"/portfolios/{portfolio_id}/transactions/",
        headers=auth_headers,
        json={
            "asset_id": asset_id,
            "transaction_type": "sell",
            "quantity": "8",
            "price": "10",
            "fees": "0",
            "transaction_date": "2026-08-02",
        },
    )
    assert sell_response.status_code == 201

    delete_response = client.delete(
        f"/transactions/{buy_id}",
        headers=auth_headers,
    )

    assert delete_response.status_code == 400
    assert "negative quantity" in delete_response.json()["detail"]

    stored_response = client.get(
        f"/transactions/{buy_id}",
        headers=auth_headers,
    )
    assert stored_response.status_code == 200
