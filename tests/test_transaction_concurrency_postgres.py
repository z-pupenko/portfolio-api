import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.database import engine
from app.models import Portfolio, Transaction
from app.schemas import TransactionCreate
from app.services.transactions import TransactionRuleError, add_transaction

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1",
    reason="PostgreSQL integration tests are disabled",
)


@pytest.fixture
def postgres_holding():
    symbol = f"LOCK{uuid4().hex[:8]}".upper()
    email = f"lock-{uuid4().hex}@example.com"

    with engine.begin() as connection:
        user_id = connection.execute(
            text(
                """
                INSERT INTO users (email, password_hash)
                VALUES (:email, :password_hash)
                RETURNING id
                """
            ),
            {"email": email, "password_hash": "test-hash"},
        ).scalar_one()
        portfolio_id = connection.execute(
            text(
                """
                INSERT INTO portfolios (
                    user_id,
                    name,
                    starting_cash,
                    base_currency
                )
                VALUES (:user_id, :name, :starting_cash, :base_currency)
                RETURNING id
                """
            ),
            {
                "user_id": user_id,
                "name": "Concurrency test",
                "starting_cash": Decimal("1000"),
                "base_currency": "GBP",
            },
        ).scalar_one()
        asset_id = connection.execute(
            text(
                """
                INSERT INTO assets (symbol, name, asset_type, currency)
                VALUES (:symbol, :name, :asset_type, :currency)
                RETURNING id
                """
            ),
            {
                "symbol": symbol,
                "name": "Concurrency Test Asset",
                "asset_type": "stock",
                "currency": "GBP",
            },
        ).scalar_one()
        connection.execute(
            text(
                """
                INSERT INTO transactions (
                    portfolio_id,
                    asset_id,
                    transaction_type,
                    quantity,
                    price,
                    fees,
                    transaction_date
                )
                VALUES (
                    :portfolio_id,
                    :asset_id,
                    'buy',
                    10,
                    10,
                    0,
                    :transaction_date
                )
                """
            ),
            {
                "portfolio_id": portfolio_id,
                "asset_id": asset_id,
                "transaction_date": date(2026, 8, 1),
            },
        )

    yield portfolio_id, asset_id

    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM transactions WHERE portfolio_id = :portfolio_id"),
            {"portfolio_id": portfolio_id},
        )
        connection.execute(
            text("DELETE FROM assets WHERE id = :asset_id"),
            {"asset_id": asset_id},
        )
        connection.execute(
            text("DELETE FROM portfolios WHERE id = :portfolio_id"),
            {"portfolio_id": portfolio_id},
        )
        connection.execute(
            text("DELETE FROM users WHERE id = :user_id"),
            {"user_id": user_id},
        )


def test_portfolio_lock_prevents_two_concurrent_oversells(postgres_holding):
    portfolio_id, asset_id = postgres_holding
    first_flushed = Event()
    allow_first_commit = Event()
    second_started = Event()
    second_finished = Event()

    sell_data = TransactionCreate(
        asset_id=asset_id,
        transaction_type="sell",
        quantity=Decimal("8"),
        price=Decimal("10"),
        fees=Decimal("0"),
        transaction_date=date(2026, 8, 2),
    )

    def commit_first_sell() -> str:
        with Session(engine) as db:
            portfolio = db.get(Portfolio, portfolio_id)
            assert portfolio is not None
            add_transaction(db, portfolio, sell_data)
            first_flushed.set()
            assert allow_first_commit.wait(timeout=5)
            db.commit()
            return "committed"

    def attempt_second_sell() -> str:
        assert first_flushed.wait(timeout=5)

        with Session(engine) as db:
            portfolio = db.get(Portfolio, portfolio_id)
            assert portfolio is not None
            second_started.set()

            try:
                add_transaction(db, portfolio, sell_data)
                db.commit()
                return "committed"
            except TransactionRuleError:
                db.rollback()
                return "rejected"
            finally:
                second_finished.set()

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(commit_first_sell)
        assert first_flushed.wait(timeout=5)

        second_future = executor.submit(attempt_second_sell)
        assert second_started.wait(timeout=5)

        second_was_blocked = not second_finished.wait(timeout=0.2)
        allow_first_commit.set()

        outcomes = {first_future.result(), second_future.result()}

    assert second_was_blocked
    assert outcomes == {"committed", "rejected"}

    with Session(engine) as db:
        sell_count = db.scalar(
            select(func.count(Transaction.id)).where(
                Transaction.portfolio_id == portfolio_id,
                Transaction.transaction_type == "sell",
            )
        )

    assert sell_count == 1
