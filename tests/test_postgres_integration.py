import os
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.database import engine

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1",
    reason="PostgreSQL integration tests are disabled",
)


def test_migrations_create_expected_tables():
    table_names = set(inspect(engine).get_table_names())

    assert {
        "alembic_version",
        "asset_prices",
        "assets",
        "portfolios",
        "transactions",
    } <= table_names


def test_postgres_rejects_unsupported_transaction_type():
    with engine.begin() as connection:
        portfolio_id = connection.execute(
            text(
                """
                INSERT INTO portfolios (name, starting_cash, base_currency)
                VALUES (:name, :starting_cash, :base_currency)
                RETURNING id
                """
            ),
            {
                "name": "PostgreSQL constraint test",
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
                "symbol": "PGTEST",
                "name": "PostgreSQL Test Asset",
                "asset_type": "stock",
                "currency": "GBP",
            },
        ).scalar_one()

    try:
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
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
                            :transaction_type,
                            :quantity,
                            :price,
                            :fees,
                            :transaction_date
                        )
                        """
                    ),
                    {
                        "portfolio_id": portfolio_id,
                        "asset_id": asset_id,
                        "transaction_type": "gift",
                        "quantity": Decimal("1"),
                        "price": Decimal("10"),
                        "fees": Decimal("0"),
                        "transaction_date": date(2026, 8, 14),
                    },
                )
    finally:
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM assets WHERE id = :asset_id"),
                {"asset_id": asset_id},
            )
            connection.execute(
                text("DELETE FROM portfolios WHERE id = :portfolio_id"),
                {"portfolio_id": portfolio_id},
            )
