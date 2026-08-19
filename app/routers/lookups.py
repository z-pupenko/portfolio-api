from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, Portfolio, Transaction


def get_portfolio_or_404(
    db: Session,
    portfolio_id: int,
    user_id: int,
) -> Portfolio:
    portfolio = db.scalar(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
        )
    )

    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )

    return portfolio


def get_asset_or_404(
    db: Session,
    asset_id: int,
) -> Asset:
    asset = db.get(Asset, asset_id)

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    return asset


def get_transaction_or_404(
    db: Session,
    transaction_id: int,
    user_id: int,
) -> Transaction:
    transaction = db.scalar(
        select(Transaction)
        .join(Portfolio, Transaction.portfolio_id == Portfolio.id)
        .where(
            Transaction.id == transaction_id,
            Portfolio.user_id == user_id,
        )
    )

    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    return transaction
