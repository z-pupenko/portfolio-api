from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# --------------------------------------------------
# Portfolio model
# --------------------------------------------------


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    starting_cash: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    base_currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        server_default="GBP",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="portfolio",
        cascade="all, delete-orphan",
    )


# --------------------------------------------------
# Asset models
# --------------------------------------------------


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    symbol: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    asset_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="asset",
    )

    prices: Mapped[list[AssetPrice]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
    )


class AssetPrice(Base):
    __tablename__ = "asset_prices"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id"),
        nullable=False,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
    )

    priced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    asset: Mapped[Asset] = relationship(
        back_populates="prices",
    )


# --------------------------------------------------
# Transaction model
# --------------------------------------------------


class Transaction(Base):
    __tablename__ = "transactions"

    __table_args__ = (
        CheckConstraint(
            "transaction_type IN ('buy', 'sell')",
            name="ck_transactions_transaction_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id"),
        nullable=False,
    )

    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id"),
        nullable=False,
    )

    transaction_type: Mapped[str] = mapped_column(
        String(4),
        nullable=False,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 6),
        nullable=False,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
    )

    fees: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    transaction_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    portfolio: Mapped[Portfolio] = relationship(
        back_populates="transactions",
    )

    asset: Mapped[Asset] = relationship(
        back_populates="transactions",
    )
