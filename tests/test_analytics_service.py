from datetime import date
from decimal import Decimal

from app.schemas import TransactionAnalyticsFilters
from app.services.analytics import build_transaction_analytics


def test_build_transaction_analytics():
    rows = [
        {
            "asset_id": 1,
            "symbol": "AAPL",
            "currency": "USD",
            "transaction_type": "buy",
            "quantity": Decimal("5"),
            "price": Decimal("100"),
            "fees": Decimal("1.50"),
        },
        {
            "asset_id": 1,
            "symbol": "AAPL",
            "currency": "USD",
            "transaction_type": "sell",
            "quantity": Decimal("2"),
            "price": Decimal("120"),
            "fees": Decimal("2.00"),
        },
        {
            "asset_id": 2,
            "symbol": "MSFT",
            "currency": "USD",
            "transaction_type": "buy",
            "quantity": Decimal("3"),
            "price": Decimal("50"),
            "fees": Decimal("0.50"),
        },
        {
            "asset_id": 3,
            "symbol": "VUSA",
            "currency": "GBP",
            "transaction_type": "buy",
            "quantity": Decimal("4"),
            "price": Decimal("80"),
            "fees": Decimal("1.00"),
        },
    ]
    filters = TransactionAnalyticsFilters(
        start_date="2026-01-01",
        end_date="2026-06-30",
    )

    report = build_transaction_analytics(rows=rows, portfolio_id=7, filters=filters)

    assert report.portfolio_id == 7
    assert report.start_date == date(2026, 1, 1)
    assert report.end_date == date(2026, 6, 30)
    assert report.transaction_count == 4
    assert len(report.breakdown.by_asset) == 3
    assert len(report.breakdown.by_currency) == 2

    assets_by_symbol = {asset.symbol: asset for asset in report.breakdown.by_asset}
    assert assets_by_symbol["AAPL"].model_dump() == {
        "asset_id": 1,
        "symbol": "AAPL",
        "currency": "USD",
        "transaction_count": 2,
        "total_bought": Decimal("5"),
        "total_sold": Decimal("2"),
        "net_quantity": Decimal("3"),
        "gross_traded_value": Decimal("740"),
        "total_fees": Decimal("3.50"),
    }
    assert assets_by_symbol["MSFT"].gross_traded_value == Decimal("150")
    assert assets_by_symbol["VUSA"].gross_traded_value == Decimal("320")

    totals_by_currency = {item.currency: item for item in report.breakdown.by_currency}
    assert totals_by_currency["USD"].model_dump() == {
        "currency": "USD",
        "transaction_count": 3,
        "gross_traded_value": Decimal("890"),
        "total_fees": Decimal("4.00"),
    }
    assert totals_by_currency["GBP"].model_dump() == {
        "currency": "GBP",
        "transaction_count": 1,
        "gross_traded_value": Decimal("320"),
        "total_fees": Decimal("1.00"),
    }


def test_build_transaction_analytics_returns_empty_report():
    filters = TransactionAnalyticsFilters()

    report = build_transaction_analytics(
        rows=[],
        portfolio_id=7,
        filters=filters,
    )

    assert report.model_dump() == {
        "portfolio_id": 7,
        "start_date": None,
        "end_date": None,
        "transaction_count": 0,
        "breakdown": {
            "by_asset": [],
            "by_currency": [],
        },
    }
