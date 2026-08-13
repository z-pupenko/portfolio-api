from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas import TransactionUpdate


@pytest.mark.parametrize(
    "field_name",
    [
        "asset_id",
        "transaction_type",
        "quantity",
        "price",
        "fees",
        "transaction_date",
    ],
)
def test_transaction_update_rejects_explicit_null(field_name):
    with pytest.raises(ValidationError):
        TransactionUpdate(**{field_name: None})


def test_transaction_update_allows_partial_update():
    update = TransactionUpdate(
        quantity=Decimal("8"),
    )

    assert update.model_dump(exclude_unset=True) == {
        "quantity": Decimal("8"),
    }
