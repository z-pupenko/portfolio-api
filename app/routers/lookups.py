from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Asset, Portfolio, Transaction


def get_portfolio_or_404(
    db: Session,
    portfolio_id: int,
) -> Portfolio:
    portfolio = db.get(Portfolio, portfolio_id)

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
) -> Transaction:
    transaction = db.get(Transaction, transaction_id)

    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    return transaction
