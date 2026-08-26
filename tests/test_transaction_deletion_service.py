from datetime import date
from decimal import Decimal

import pytest

from app.models import Asset, Portfolio, Transaction, User
from app.services.transactions import (
    TransactionRuleError,
    validate_transaction_deletion,
)


def create_ledger(db_session, starting_cash: Decimal):
    user = User(
        email="deletion-service@example.com",
        password_hash="test-hash",
    )
    portfolio = Portfolio(
        user=user,
        name="Deletion rules",
        starting_cash=starting_cash,
        base_currency="GBP",
    )
    asset = Asset(
        symbol="DELTEST",
        name="Deletion Test Asset",
        asset_type="stock",
        currency="GBP",
    )

    db_session.add_all([user, portfolio, asset])
    db_session.commit()

    return portfolio, asset


def make_transaction(
    portfolio: Portfolio,
    asset: Asset,
    transaction_type: str,
    quantity: str,
    price: str,
    day: int,
) -> Transaction:
    return Transaction(
        portfolio_id=portfolio.id,
        asset_id=asset.id,
        transaction_type=transaction_type,
        quantity=Decimal(quantity),
        price=Decimal(price),
        fees=Decimal("0"),
        transaction_date=date(2026, 8, day),
    )


def test_rejects_deleting_buy_that_would_leave_negative_quantity(db_session):
    portfolio, asset = create_ledger(db_session, Decimal("1000"))
    buy = make_transaction(portfolio, asset, "buy", "10", "10", 1)
    sell = make_transaction(portfolio, asset, "sell", "8", "10", 2)
    db_session.add_all([buy, sell])
    db_session.commit()

    with pytest.raises(TransactionRuleError, match="negative quantity"):
        validate_transaction_deletion(db_session, portfolio, buy)


def test_rejects_deleting_sell_that_would_leave_negative_cash(db_session):
    portfolio, asset = create_ledger(db_session, Decimal("100"))
    initial_buy = make_transaction(portfolio, asset, "buy", "10", "10", 1)
    sell = make_transaction(portfolio, asset, "sell", "5", "20", 2)
    later_buy = make_transaction(portfolio, asset, "buy", "5", "10", 3)
    db_session.add_all([initial_buy, sell, later_buy])
    db_session.commit()

    with pytest.raises(TransactionRuleError, match="negative cash balance"):
        validate_transaction_deletion(db_session, portfolio, sell)


def test_allows_deleting_buy_when_remaining_quantity_is_zero(db_session):
    portfolio, asset = create_ledger(db_session, Decimal("1000"))
    buy = make_transaction(portfolio, asset, "buy", "10", "10", 1)
    db_session.add(buy)
    db_session.commit()

    validate_transaction_deletion(db_session, portfolio, buy)
