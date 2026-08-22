from decimal import Decimal

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, Transaction
from app.schemas import TransactionAnalyticsFilters, TransactionAnalyticsResponse


def fetch_transaction_analytics_rows(
    db: Session,
    portfolio_id: int,
    filters: TransactionAnalyticsFilters,
) -> list[dict[str, object]]:
    statement = (
        select(
            Transaction.asset_id,
            Asset.symbol,
            Asset.currency,
            Transaction.transaction_type,
            Transaction.quantity,
            Transaction.price,
            Transaction.fees,
        )
        .join(
            Asset,
            Transaction.asset_id == Asset.id,
        )
        .where(Transaction.portfolio_id == portfolio_id)
    )
    if filters.start_date is not None:
        statement = statement.where(Transaction.transaction_date >= filters.start_date)

    if filters.end_date is not None:
        statement = statement.where(Transaction.transaction_date <= filters.end_date)

    rows = db.execute(statement).mappings().all()

    return [dict(row) for row in rows]


def build_transaction_analytics(
    rows: list[dict[str, object]],
    portfolio_id: int,
    filters: TransactionAnalyticsFilters,
) -> TransactionAnalyticsResponse:
    if not rows:
        return TransactionAnalyticsResponse(
            portfolio_id=portfolio_id,
            start_date=filters.start_date,
            end_date=filters.end_date,
            transaction_count=0,
            breakdown={
                "by_asset": [],
                "by_currency": [],
            },
        )

    frame = pd.DataFrame(rows)
    frame["gross_traded_value"] = frame["quantity"] * frame["price"]

    is_buy = frame["transaction_type"] == "buy"
    is_sell = frame["transaction_type"] == "sell"

    frame["bought_quantity"] = frame["quantity"].where(
        is_buy,
        Decimal("0"),
    )

    frame["sold_quantity"] = frame["quantity"].where(
        is_sell,
        Decimal("0"),
    )

    frame["net_quantity"] = frame["bought_quantity"] - frame["sold_quantity"]

    asset_summary = frame.groupby(
        ["asset_id", "symbol", "currency"],
        as_index=False,
    ).agg(
        transaction_count=("transaction_type", "size"),
        total_bought=("bought_quantity", "sum"),
        total_sold=("sold_quantity", "sum"),
        net_quantity=("net_quantity", "sum"),
        gross_traded_value=("gross_traded_value", "sum"),
        total_fees=("fees", "sum"),
    )

    currency_summary = frame.groupby(
        "currency",
        as_index=False,
    ).agg(
        transaction_count=("transaction_type", "size"),
        gross_traded_value=("gross_traded_value", "sum"),
        total_fees=("fees", "sum"),
    )

    asset_records = asset_summary.to_dict(orient="records")
    currency_records = currency_summary.to_dict(orient="records")

    return TransactionAnalyticsResponse(
        portfolio_id=portfolio_id,
        start_date=filters.start_date,
        end_date=filters.end_date,
        transaction_count=len(rows),
        breakdown={
            "by_asset": asset_records,
            "by_currency": currency_records,
        },
    )
