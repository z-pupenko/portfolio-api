from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas import TransactionAnalyticsFilters, TransactionUpdate


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


def test_transaction_analytics_filters_accept_valid_date_range():
    filters = TransactionAnalyticsFilters(
        start_date="2026-01-01",
        end_date="2026-06-30",
    )

    assert filters.start_date == date(2026, 1, 1)
    assert filters.end_date == date(2026, 6, 30)


def test_transaction_analytics_filters_reject_backwards_date_range():
    with pytest.raises(
        ValidationError,
        match="start_date must be on or before end_date",
    ):
        TransactionAnalyticsFilters(
            start_date="2026-08-01",
            end_date="2026-06-30",
        )
