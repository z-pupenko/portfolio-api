from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Asset, Portfolio, Transaction, User
from app.services.portfolios import calculate_holdings


def test_holdings_query_filters_by_portfolio(
    db_session: Session,
):
    user = User(
        email="integration@example.com",
        password_hash="test-hash",
    )

    growth = Portfolio(
        user=user,
        name="Growth",
        starting_cash=Decimal("10000"),
        base_currency="GBP",
    )

    retirement = Portfolio(
        user=user,
        name="Retirement",
        starting_cash=Decimal("20000"),
        base_currency="GBP",
    )

    aapl = Asset(
        symbol="AAPL",
        name="Apple",
        asset_type="stock",
        currency="GBP",
    )

    db_session.add_all(
        [
            growth,
            retirement,
            aapl,
            user,
        ]
    )
    db_session.flush()

    transactions = [
        Transaction(
            portfolio_id=growth.id,
            asset_id=aapl.id,
            transaction_type="buy",
            quantity=Decimal("10"),
            price=Decimal("100"),
            fees=Decimal("0"),
            transaction_date=date(2026, 1, 1),
        ),
        Transaction(
            portfolio_id=growth.id,
            asset_id=aapl.id,
            transaction_type="sell",
            quantity=Decimal("3"),
            price=Decimal("120"),
            fees=Decimal("0"),
            transaction_date=date(2026, 2, 1),
        ),
        Transaction(
            portfolio_id=retirement.id,
            asset_id=aapl.id,
            transaction_type="buy",
            quantity=Decimal("50"),
            price=Decimal("100"),
            fees=Decimal("0"),
            transaction_date=date(2026, 1, 1),
        ),
    ]

    db_session.add_all(transactions)
    db_session.commit()

    result = calculate_holdings(
        db_session,
        portfolio_id=growth.id,
    )

    assert result == [
        {
            "asset_id": aapl.id,
            "symbol": "AAPL",
            "currency": "GBP",
            "quantity": Decimal("7"),
        }
    ]
