from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Portfolio, Transaction
from app.schemas import TransactionCreate
from app.services.portfolios import (
    calculate_asset_quantity,
    calculate_cash_balance,
)


class TransactionRuleError(ValueError):
    """Raised when a transaction violates a portfolio rule."""


def validate_sufficient_cash(
    db: Session,
    portfolio: Portfolio,
    quantity: Decimal,
    price: Decimal,
    fees: Decimal,
    exclude_transaction_id: int | None = None,
) -> None:
    available_cash = calculate_cash_balance(
        db,
        portfolio,
        exclude_transaction_id=exclude_transaction_id,
    )
    required_cash = quantity * price + fees

    if required_cash > available_cash:
        raise TransactionRuleError(
            f"Insufficient cash. Available: {available_cash}, required: {required_cash}"
        )


def validate_sufficient_quantity(
    db: Session,
    portfolio_id: int,
    asset_id: int,
    quantity: Decimal,
    exclude_transaction_id: int | None = None,
    available_quantity_label: str = "Available quantity is",
) -> None:
    available_quantity = calculate_asset_quantity(
        db,
        portfolio_id,
        asset_id,
        exclude_transaction_id=exclude_transaction_id,
    )

    if quantity > available_quantity:
        raise TransactionRuleError(
            f"Cannot sell {quantity}. {available_quantity_label} {available_quantity}"
        )


def add_transaction(
    db: Session,
    portfolio: Portfolio,
    transaction_data: TransactionCreate,
) -> Transaction:
    if transaction_data.transaction_type == "sell":
        validate_sufficient_quantity(
            db,
            portfolio.id,
            transaction_data.asset_id,
            transaction_data.quantity,
            available_quantity_label="Current holding is",
        )
    elif transaction_data.transaction_type == "buy":
        validate_sufficient_cash(
            db,
            portfolio,
            transaction_data.quantity,
            transaction_data.price,
            transaction_data.fees,
        )
    else:
        raise RuntimeError(
            f"Unsupported transaction type: {transaction_data.transaction_type}"
        )

    transaction = Transaction(
        portfolio_id=portfolio.id,
        **transaction_data.model_dump(),
    )
    db.add(transaction)
    db.flush()

    return transaction
