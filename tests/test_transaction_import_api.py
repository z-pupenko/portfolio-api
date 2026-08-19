from decimal import Decimal

from fastapi.testclient import TestClient


def test_import_transactions_csv(
    client: TestClient,
    auth_headers: dict[str, str],
):
    portfolio_response = client.post(
        "/portfolios/",
        json={
            "name": "Growth",
            "starting_cash": "10000",
            "base_currency": "GBP",
        },
        headers=auth_headers,
    )
    assert portfolio_response.status_code == 201
    portfolio_id = portfolio_response.json()["id"]

    aapl_response = client.post(
        "/assets/",
        headers=auth_headers,
        json={
            "symbol": "AAPL",
            "name": "Apple",
            "asset_type": "stock",
            "currency": "GBP",
        },
    )
    assert aapl_response.status_code == 201

    msft_response = client.post(
        "/assets/",
        headers=auth_headers,
        json={
            "symbol": "MSFT",
            "name": "Microsoft",
            "asset_type": "stock",
            "currency": "GBP",
        },
    )
    assert msft_response.status_code == 201

    aapl_id = aapl_response.json()["id"]
    msft_id = msft_response.json()["id"]
    csv_content = (
        "asset_id,transaction_type,quantity,"
        "price,fees,transaction_date\n"
        f"{aapl_id},buy,10,150.25,1.50,2026-08-01\n"
        f"{msft_id},buy,5,400,0,2026-08-02\n"
        f"{aapl_id},sell,3,160,1,2026-08-05\n"
    )

    response = client.post(
        f"/portfolios/{portfolio_id}/transactions/import/",
        files={
            "file": (
                "transactions.csv",
                csv_content,
                "text/csv",
            )
        },
        headers=auth_headers,
    )
    assert response.status_code == 201

    response_data = response.json()
    summary_by_asset = {item["asset_id"]: item for item in response_data["summary"]}
    aapl_summary = summary_by_asset[aapl_id]

    assert aapl_summary["transaction_count"] == 2
    assert Decimal(aapl_summary["net_quantity"]) == Decimal("7")
    assert Decimal(aapl_summary["gross_traded_value"]) == Decimal("1982.50")
    assert Decimal(aapl_summary["total_fees"]) == Decimal("2.50")
    assert response_data["imported_count"] == 3
    assert len(response_data["transactions"]) == 3
    assert response_data["transactions"][0]["asset_id"] == aapl_id

    stored_response = client.get(
        f"/portfolios/{portfolio_id}/transactions/",
        headers=auth_headers,
    )
    assert stored_response.status_code == 200
    assert len(stored_response.json()) == 3
