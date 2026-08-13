from typing import BinaryIO

import pandas as pd
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models import Asset, Portfolio, Transaction
from app.schemas import TransactionCreate
from app.services.transactions import (
    TransactionRuleError,
    add_transaction,
)

REQUIRED_COLUMNS = {
    "asset_id",
    "transaction_type",
    "quantity",
    "price",
    "transaction_date",
}

OPTIONAL_COLUMNS = {
    "fees",
}

ALLOWED_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS


class TransactionCSVFormatError(ValueError):
    pass


class TransactionCSVValidationError(ValueError):
    def __init__(
        self,
        errors: list[dict[str, object]],
    ) -> None:
        super().__init__("CSV contains invalid transaction rows")
        self.errors = errors


class TransactionCSVImportError(ValueError):
    def __init__(
        self,
        row: int,
        message: str,
    ) -> None:
        self.row = row
        self.message = message

        super().__init__(f"CSV row {row}: {message}")


def prepare_transaction_dataframe(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    prepared = dataframe.copy()

    prepared.columns = prepared.columns.str.strip()

    for column in prepared.columns:
        prepared[column] = prepared[column].str.strip()

    actual_columns = set(prepared.columns)

    missing_columns = REQUIRED_COLUMNS - actual_columns

    if missing_columns:
        missing_names = ", ".join(sorted(missing_columns))

        raise TransactionCSVFormatError(f"Missing required columns: {missing_names}")

    unexpected_columns = actual_columns - ALLOWED_COLUMNS

    if unexpected_columns:
        unexpected_names = ", ".join(sorted(unexpected_columns))

        raise TransactionCSVFormatError(f"Unexpected columns: {unexpected_names}")

    if prepared.empty:
        raise TransactionCSVFormatError("CSV contains no transaction rows")

    prepared["transaction_type"] = prepared["transaction_type"].str.lower()

    if "fees" not in prepared.columns:
        prepared["fees"] = "0"
    else:
        prepared.loc[
            prepared["fees"] == "",
            "fees",
        ] = "0"

    return prepared


def parse_transaction_csv(
    file: BinaryIO,
) -> list[TransactionCreate]:
    try:
        dataframe = pd.read_csv(
            file,
            dtype=str,
            keep_default_na=False,
        )
    except pd.errors.EmptyDataError as error:
        raise TransactionCSVFormatError("CSV file is empty") from error
    except pd.errors.ParserError as error:
        raise TransactionCSVFormatError("CSV file is malformed") from error
    except UnicodeDecodeError as error:
        raise TransactionCSVFormatError("CSV file must use UTF-8 encoding") from error

    dataframe = prepare_transaction_dataframe(dataframe)

    records = dataframe.to_dict(orient="records")

    transactions: list[TransactionCreate] = []
    validation_errors: list[dict[str, object]] = []

    for row_number, record in enumerate(
        records,
        start=2,
    ):
        try:
            transaction = TransactionCreate.model_validate(record)
        except ValidationError as error:
            for issue in error.errors(include_url=False):
                field = ".".join(str(part) for part in issue["loc"])

                validation_errors.append(
                    {
                        "row": row_number,
                        "field": field,
                        "message": issue["msg"],
                    }
                )
        else:
            transactions.append(transaction)

    if validation_errors:
        raise TransactionCSVValidationError(validation_errors)

    return transactions


def import_transaction_batch(
    db: Session,
    portfolio: Portfolio,
    transaction_rows: list[TransactionCreate],
) -> list[Transaction]:
    imported_transactions: list[Transaction] = []

    try:
        for row_number, transaction_data in enumerate(
            transaction_rows,
            start=2,
        ):
            asset = db.get(
                Asset,
                transaction_data.asset_id,
            )

            if asset is None:
                raise TransactionCSVImportError(
                    row_number,
                    (f"Asset {transaction_data.asset_id} does not exist"),
                )

            try:
                transaction = add_transaction(
                    db,
                    portfolio,
                    transaction_data,
                )
            except TransactionRuleError as error:
                raise TransactionCSVImportError(
                    row_number,
                    str(error),
                ) from error

            imported_transactions.append(transaction)

        db.commit()

    except Exception:
        db.rollback()
        raise

    return imported_transactions


def build_transaction_summary(
    transaction_rows: list[TransactionCreate],
) -> list[dict[str, object]]:
    dataframe = pd.DataFrame(
        [transaction.model_dump() for transaction in transaction_rows]
    )

    is_buy = dataframe["transaction_type"] == "buy"

    dataframe["signed_quantity"] = dataframe["quantity"].where(
        is_buy,
        -dataframe["quantity"],
    )

    dataframe["gross_value"] = dataframe["quantity"] * dataframe["price"]

    summary = (
        dataframe.groupby("asset_id", as_index=False)
        .agg(
            transaction_count=("asset_id", "size"),
            net_quantity=("signed_quantity", "sum"),
            gross_traded_value=("gross_value", "sum"),
            total_fees=("fees", "sum"),
        )
        .sort_values("asset_id")
    )

    return summary.to_dict(orient="records")
