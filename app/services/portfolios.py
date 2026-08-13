from decimal import Decimal
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, AssetPrice, Portfolio, Transaction


class Holding(TypedDict):
    asset_id: int
    symbol: str
    currency: str
    quantity: Decimal


def calculate_cash_balance(
    db: Session,
    portfolio: Portfolio,
    exclude_transaction_id: int | None = None,
) -> Decimal:
    statement = select(Transaction).where(Transaction.portfolio_id == portfolio.id)

    if exclude_transaction_id is not None:
        statement = statement.where(Transaction.id != exclude_transaction_id)

    cash_balance = portfolio.starting_cash

    for transaction in db.scalars(statement).all():
        transaction_value = transaction.quantity * transaction.price

        if transaction.transaction_type == "buy":
            cash_balance -= transaction_value + transaction.fees
        elif transaction.transaction_type == "sell":
            cash_balance += transaction_value - transaction.fees
        else:
            raise RuntimeError(
                f"Unsupported transaction type: {transaction.transaction_type}"
            )

    return cash_balance


def calculate_holdings(
    db: Session,
    portfolio_id: int,
) -> list[Holding]:
    statement = (
        select(Transaction, Asset)
        .join(Asset, Transaction.asset_id == Asset.id)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.id)
    )

    holdings: dict[int, Holding] = {}

    for transaction, asset in db.execute(statement).all():
        if asset.id not in holdings:
            holdings[asset.id] = {
                "asset_id": asset.id,
                "symbol": asset.symbol,
                "currency": asset.currency,
                "quantity": Decimal("0"),
            }

        if transaction.transaction_type == "buy":
            holdings[asset.id]["quantity"] += transaction.quantity
        elif transaction.transaction_type == "sell":
            holdings[asset.id]["quantity"] -= transaction.quantity
        else:
            raise RuntimeError(
                f"Unsupported transaction type: {transaction.transaction_type}"
            )

    return [holding for holding in holdings.values() if holding["quantity"] != 0]


def calculate_asset_quantity(
    db: Session,
    portfolio_id: int,
    asset_id: int,
    exclude_transaction_id: int | None = None,
) -> Decimal:
    statement = select(Transaction).where(
        Transaction.portfolio_id == portfolio_id,
        Transaction.asset_id == asset_id,
    )

    if exclude_transaction_id is not None:
        statement = statement.where(Transaction.id != exclude_transaction_id)

    quantity = Decimal("0")

    for transaction in db.scalars(statement).all():
        if transaction.transaction_type == "buy":
            quantity += transaction.quantity
        elif transaction.transaction_type == "sell":
            quantity -= transaction.quantity
        else:
            raise RuntimeError(
                f"Unsupported transaction type: {transaction.transaction_type}"
            )

    return quantity


def calculate_portfolio_valuation(
    db: Session,
    portfolio: Portfolio,
) -> dict[str, object]:
    holdings = calculate_holdings(db, portfolio.id)
    valued_holdings = []
    holdings_value = Decimal("0")

    for holding in holdings:
        if holding["currency"] != portfolio.base_currency:
            raise ValueError(
                f"{holding['symbol']} is priced in "
                f"{holding['currency']}, but the portfolio "
                f"base currency is {portfolio.base_currency}"
            )

        statement = (
            select(AssetPrice)
            .where(AssetPrice.asset_id == holding["asset_id"])
            .order_by(
                AssetPrice.priced_at.desc(),
                AssetPrice.id.desc(),
            )
            .limit(1)
        )
        latest_price = db.scalar(statement)

        if latest_price is None:
            raise ValueError(f"No price exists for {holding['symbol']}")

        market_value = holding["quantity"] * latest_price.price
        holdings_value += market_value
        valued_holdings.append(
            {
                **holding,
                "latest_price": latest_price.price,
                "market_value": market_value,
            }
        )

    cash_balance = calculate_cash_balance(db, portfolio)

    return {
        "portfolio_id": portfolio.id,
        "base_currency": portfolio.base_currency,
        "cash_balance": cash_balance,
        "holdings_value": holdings_value,
        "total_value": cash_balance + holdings_value,
        "holdings": valued_holdings,
    }
