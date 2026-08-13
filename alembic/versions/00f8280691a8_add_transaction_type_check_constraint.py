"""add transaction type check constraint

Revision ID: 00f8280691a8
Revises: fedc53d5539c
Create Date: 2026-07-29 17:39:20.656178

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "00f8280691a8"
down_revision: str | Sequence[str] | None = "fedc53d5539c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_transactions_transaction_type",
        "transactions",
        "transaction_type IN ('buy', 'sell')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_transactions_transaction_type",
        "transactions",
        type_="check",
    )
