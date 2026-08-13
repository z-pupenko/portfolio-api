from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.models import Asset, Portfolio, Transaction
from app.services.portfolios import (
    calculate_cash_balance,
    calculate_holdings,
)


def test_calculate_cash_balance_applies_buys_sells_and_fees():
    portfolio = Portfolio(
        id=1,
        name="Growth",
        starting_cash=Decimal("1000"),
        base_currency="GBP",
    )

    buy = Transaction(
        transaction_type="buy",
        quantity=Decimal("2"),
        price=Decimal("100"),
        fees=Decimal("5"),
    )

    sell = Transaction(
        transaction_type="sell",
        quantity=Decimal("1"),
        price=Decimal("120"),
        fees=Decimal("2"),
    )

    db = MagicMock(spec=Session)
    db.scalars.return_value.all.return_value = [
        buy,
        sell,
    ]

    result = calculate_cash_balance(
        db,
        portfolio,
    )

    assert result == Decimal("913")


def test_calculate_cash_balance_rejects_unknown_transaction_type():
    portfolio = Portfolio(
        id=1,
        name="Growth",
        starting_cash=Decimal("1000"),
        base_currency="GBP",
    )

    transaction = Transaction(
        transaction_type="gift",
        quantity=Decimal("2"),
        price=Decimal("100"),
        fees=Decimal("0"),
    )

    db = MagicMock(spec=Session)
    db.scalars.return_value.all.return_value = [transaction]

    with pytest.raises(
        RuntimeError,
        match="Unsupported transaction type: gift",
    ):
        calculate_cash_balance(
            db,
            portfolio,
        )


def test_holdings_aggregation():
    aapl = Asset(
        id=1,
        symbol="AAPL",
        name="Apple",
        asset_type="stock",
        currency="GBP",
    )

    msft = Asset(
        id=2,
        symbol="MSFT",
        name="Microsoft",
        asset_type="stock",
        currency="GBP",
    )

    aapl_buy = Transaction(
        transaction_type="buy",
        quantity=Decimal("10"),
    )

    aapl_sell = Transaction(
        transaction_type="sell",
        quantity=Decimal("3"),
    )

    msft_buy = Transaction(
        transaction_type="buy",
        quantity=Decimal("5"),
    )

    msft_sell = Transaction(
        transaction_type="sell",
        quantity=Decimal("5"),
    )

    fake_result = MagicMock()
    fake_result.all.return_value = [
        (aapl_buy, aapl),
        (aapl_sell, aapl),
        (msft_buy, msft),
        (msft_sell, msft),
    ]

    db = MagicMock(spec=Session)
    db.execute.return_value = fake_result

    result = calculate_holdings(
        db,
        portfolio_id=1,
    )

    assert result == [
        {
            "asset_id": 1,
            "symbol": "AAPL",
            "currency": "GBP",
            "quantity": Decimal("7"),
        }
    ]
