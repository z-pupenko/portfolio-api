from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models import Asset, Portfolio, Transaction, User
from app.schemas import TransactionCreate
from app.services.transaction_imports import (
    TransactionCSVFormatError,
    TransactionCSVImportError,
    TransactionCSVValidationError,
    build_transaction_summary,
    import_transaction_batch,
    parse_transaction_csv,
)

FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures"


def test_parse_valid_transaction_csv():
    csv_path = FIXTURES_DIRECTORY / "transactions_valid.csv"

    with csv_path.open("rb") as file:
        transactions = parse_transaction_csv(file)

    assert len(transactions) == 3

    first_transaction = transactions[0]

    assert first_transaction.asset_id == 1
    assert first_transaction.transaction_type == "buy"
    assert first_transaction.quantity == Decimal("10")
    assert first_transaction.price == Decimal("150.25")
    assert first_transaction.fees == Decimal("1.50")
    assert first_transaction.transaction_date == date(
        2026,
        8,
        1,
    )

    assert transactions[2].transaction_type == "sell"


def test_parse_csv_rejects_missing_required_columns():
    csv_file = BytesIO(b"asset_id,transaction_type,quantity,price\n1,buy,10,150.25\n")

    with pytest.raises(
        ValueError,
        match=("Missing required columns: transaction_date"),
    ):
        parse_transaction_csv(csv_file)


def test_parse_csv_collects_row_validation_errors():
    csv_file = BytesIO(
        b"asset_id,transaction_type,quantity,"
        b"price,fees,transaction_date\n"
        b"1,buy,10,100,0,2026-08-01\n"
        b"0,hold,-2,100,0,2026-08-02\n"
        b"2,buy,1,0,-1,2026-08-03\n"
    )

    with pytest.raises(TransactionCSVValidationError) as exception_info:
        parse_transaction_csv(csv_file)

    error_locations = {
        (error["row"], error["field"]) for error in exception_info.value.errors
    }

    assert error_locations == {
        (3, "asset_id"),
        (3, "transaction_type"),
        (3, "quantity"),
        (4, "price"),
        (4, "fees"),
    }


def test_import_batch_rolls_back_when_later_row_fails(
    db_session,
):
    user = User(
        email="import@example.com",
        password_hash="test-hash",
    )

    portfolio = Portfolio(
        user=user,
        name="Growth",
        starting_cash=Decimal("1000"),
        base_currency="GBP",
    )

    asset = Asset(
        symbol="AAPL",
        name="Apple",
        asset_type="stock",
        currency="GBP",
    )

    db_session.add_all(
        [
            portfolio,
            asset,
            user,
        ]
    )
    db_session.commit()

    transaction_rows = [
        TransactionCreate(
            asset_id=asset.id,
            transaction_type="buy",
            quantity=Decimal("5"),
            price=Decimal("100"),
            fees=Decimal("0"),
            transaction_date=date(2026, 8, 1),
        ),
        TransactionCreate(
            asset_id=asset.id,
            transaction_type="sell",
            quantity=Decimal("6"),
            price=Decimal("110"),
            fees=Decimal("0"),
            transaction_date=date(2026, 8, 2),
        ),
    ]

    with pytest.raises(
        TransactionCSVImportError,
        match="CSV row 3",
    ):
        import_transaction_batch(
            db_session,
            portfolio,
            transaction_rows,
        )

    stored_transactions = db_session.scalars(select(Transaction)).all()

    assert stored_transactions == []


def test_parse_csv_normalizes_values_and_defaults_fees():
    csv_file = BytesIO(
        b" asset_id , transaction_type , quantity ,"
        b" price , transaction_date \n"
        b" 1 , BUY , 2 , 10.50 , 2026-08-01 \n"
    )

    transactions = parse_transaction_csv(csv_file)

    assert len(transactions) == 1

    transaction = transactions[0]

    assert transaction.asset_id == 1
    assert transaction.transaction_type == "buy"
    assert transaction.quantity == Decimal("2")
    assert transaction.price == Decimal("10.50")
    assert transaction.fees == Decimal("0")
    assert transaction.transaction_date == date(
        2026,
        8,
        1,
    )


@pytest.mark.parametrize(
    (
        "csv_content",
        "expected_message",
    ),
    [
        (
            b"",
            "CSV file is empty",
        ),
        (
            (b"asset_id,transaction_type,quantity,price,transaction_date\n"),
            "CSV contains no transaction rows",
        ),
        (
            (
                b"asset_id,transaction_type,quantity,"
                b"price,transaction_date\n"
                b'1,buy,"10,100,2026-08-01\n'
            ),
            "CSV file is malformed",
        ),
    ],
)
def test_parse_csv_rejects_invalid_file_format(
    csv_content,
    expected_message,
):
    with pytest.raises(
        TransactionCSVFormatError,
        match=expected_message,
    ):
        parse_transaction_csv(BytesIO(csv_content))


def test_build_transaction_summary():
    csv_path = FIXTURES_DIRECTORY / "transactions_valid.csv"

    with csv_path.open("rb") as file:
        transaction_rows = parse_transaction_csv(file)

    summary = build_transaction_summary(transaction_rows)

    assert summary == [
        {
            "asset_id": 1,
            "transaction_count": 2,
            "net_quantity": Decimal("7"),
            "gross_traded_value": Decimal("1982.50"),
            "total_fees": Decimal("2.50"),
        },
        {
            "asset_id": 2,
            "transaction_count": 1,
            "net_quantity": Decimal("5"),
            "gross_traded_value": Decimal("2000"),
            "total_fees": Decimal("0"),
        },
    ]
