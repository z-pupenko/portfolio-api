"""add financial constraints and indexes

Revision ID: 149957d84f0e
Revises: 00f8280691a8
Create Date: 2026-08-14 15:41:12.242911

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "149957d84f0e"
down_revision: str | Sequence[str] | None = "00f8280691a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_check_constraint(
        "ck_portfolios_starting_cash_non_negative",
        "portfolios",
        "starting_cash >= 0",
    )
    op.create_check_constraint(
        "ck_asset_prices_price_positive",
        "asset_prices",
        "price > 0",
    )
    op.create_check_constraint(
        "ck_transactions_quantity_positive",
        "transactions",
        "quantity > 0",
    )
    op.create_check_constraint(
        "ck_transactions_price_positive",
        "transactions",
        "price > 0",
    )
    op.create_check_constraint(
        "ck_transactions_fees_non_negative",
        "transactions",
        "fees >= 0",
    )

    op.create_index(
        "ix_asset_prices_asset_id_priced_at_id",
        "asset_prices",
        [
            "asset_id",
            sa.literal_column("priced_at DESC"),
            sa.literal_column("id DESC"),
        ],
        unique=False,
    )
    op.create_index(
        "ix_transactions_portfolio_id_asset_id",
        "transactions",
        ["portfolio_id", "asset_id"],
        unique=False,
    )
    op.create_index(
        "ix_transactions_portfolio_id_id",
        "transactions",
        ["portfolio_id", "id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_transactions_portfolio_id_id", table_name="transactions")
    op.drop_index(
        "ix_transactions_portfolio_id_asset_id",
        table_name="transactions",
    )
    op.drop_index(
        "ix_asset_prices_asset_id_priced_at_id",
        table_name="asset_prices",
    )

    op.drop_constraint(
        "ck_transactions_fees_non_negative",
        "transactions",
        type_="check",
    )
    op.drop_constraint(
        "ck_transactions_price_positive",
        "transactions",
        type_="check",
    )
    op.drop_constraint(
        "ck_transactions_quantity_positive",
        "transactions",
        type_="check",
    )
    op.drop_constraint(
        "ck_asset_prices_price_positive",
        "asset_prices",
        type_="check",
    )
    op.drop_constraint(
        "ck_portfolios_starting_cash_non_negative",
        "portfolios",
        type_="check",
    )
