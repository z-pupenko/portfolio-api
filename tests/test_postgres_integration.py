import os
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.database import engine

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1",
    reason="PostgreSQL integration tests are disabled",
)


@pytest.fixture
def postgres_portfolio_and_asset():
    symbol = f"PG{uuid4().hex[:10]}".upper()

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
                "symbol": symbol,
                "name": "PostgreSQL Test Asset",
                "asset_type": "stock",
                "currency": "GBP",
            },
        ).scalar_one()

    yield portfolio_id, asset_id

    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM transactions WHERE portfolio_id = :portfolio_id"),
            {"portfolio_id": portfolio_id},
        )
        connection.execute(
            text("DELETE FROM asset_prices WHERE asset_id = :asset_id"),
            {"asset_id": asset_id},
        )
        connection.execute(
            text("DELETE FROM assets WHERE id = :asset_id"),
            {"asset_id": asset_id},
        )
        connection.execute(
            text("DELETE FROM portfolios WHERE id = :portfolio_id"),
            {"portfolio_id": portfolio_id},
        )


def test_migrations_create_expected_schema_objects():
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    assert {
        "alembic_version",
        "asset_prices",
        "assets",
        "portfolios",
        "transactions",
    } <= table_names

    portfolio_checks = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("portfolios")
    }
    asset_price_checks = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("asset_prices")
    }
    transaction_checks = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("transactions")
    }

    assert "ck_portfolios_starting_cash_non_negative" in portfolio_checks
    assert "ck_asset_prices_price_positive" in asset_price_checks
    assert {
        "ck_transactions_fees_non_negative",
        "ck_transactions_price_positive",
        "ck_transactions_quantity_positive",
        "ck_transactions_transaction_type",
    } <= transaction_checks

    transaction_indexes = {
        index["name"] for index in inspector.get_indexes("transactions")
    }
    asset_price_indexes = {
        index["name"] for index in inspector.get_indexes("asset_prices")
    }

    assert {
        "ix_transactions_portfolio_id_asset_id",
        "ix_transactions_portfolio_id_id",
    } <= transaction_indexes
    assert "ix_asset_prices_asset_id_priced_at_id" in asset_price_indexes


@pytest.mark.parametrize(
    ("transaction_type", "quantity", "price", "fees"),
    [
        ("gift", Decimal("1"), Decimal("10"), Decimal("0")),
        ("buy", Decimal("0"), Decimal("10"), Decimal("0")),
        ("buy", Decimal("1"), Decimal("0"), Decimal("0")),
        ("buy", Decimal("1"), Decimal("10"), Decimal("-1")),
    ],
    ids=[
        "unsupported-type",
        "zero-quantity",
        "zero-price",
        "negative-fees",
    ],
)
def test_postgres_rejects_invalid_transaction_values(
    postgres_portfolio_and_asset,
    transaction_type,
    quantity,
    price,
    fees,
):
    portfolio_id, asset_id = postgres_portfolio_and_asset

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
                    "transaction_type": transaction_type,
                    "quantity": quantity,
                    "price": price,
                    "fees": fees,
                    "transaction_date": date(2026, 8, 14),
                },
            )


def test_postgres_rejects_negative_starting_cash():
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO portfolios (name, starting_cash, base_currency)
                    VALUES (:name, :starting_cash, :base_currency)
                    """
                ),
                {
                    "name": "Invalid cash test",
                    "starting_cash": Decimal("-1"),
                    "base_currency": "GBP",
                },
            )


def test_postgres_rejects_non_positive_asset_price(
    postgres_portfolio_and_asset,
):
    _, asset_id = postgres_portfolio_and_asset

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO asset_prices (asset_id, price)
                    VALUES (:asset_id, :price)
                    """
                ),
                {
                    "asset_id": asset_id,
                    "price": Decimal("0"),
                },
            )
