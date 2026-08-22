"""add transaction summary index

Revision ID: 7c8e3f2a1b4d
Revises: 42410853c13e
Create Date: 2026-08-22

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c8e3f2a1b4d"
down_revision: str | Sequence[str] | None = "42410853c13e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "ix_transactions_portfolio_id_transaction_date",
        "transactions",
        ["portfolio_id", "transaction_date"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_transactions_portfolio_id_transaction_date",
        table_name="transactions",
    )
