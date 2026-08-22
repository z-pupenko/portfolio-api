from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

# --------------------------------------------------
# User schemas
# --------------------------------------------------


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class UserCreate(BaseModel):
    email: EmailStr = Field(max_length=320)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------
# Portfolio schemas
# --------------------------------------------------


class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    starting_cash: Decimal = Field(ge=0)

    base_currency: str = Field(
        default="GBP",
        min_length=3,
        max_length=3,
    )


class PortfolioResponse(PortfolioCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PortfolioUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )
    description: str | None = None
    starting_cash: Decimal | None = Field(
        default=None,
        ge=0,
    )
    base_currency: str | None = Field(
        default=None,
        min_length=3,
        max_length=3,
    )


# --------------------------------------------------
# Asset schemas
# --------------------------------------------------


class AssetCreate(BaseModel):
    symbol: str = Field(
        min_length=1,
        max_length=20,
    )

    name: str = Field(
        min_length=1,
        max_length=100,
    )

    asset_type: str = Field(
        min_length=1,
        max_length=30,
    )

    currency: str = Field(
        min_length=3,
        max_length=3,
    )


class AssetResponse(AssetCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------
# Transaction schemas
# --------------------------------------------------


class TransactionAnalyticsAssetResponse(BaseModel):
    asset_id: int
    symbol: str
    currency: str
    transaction_count: int
    total_bought: Decimal
    total_sold: Decimal
    net_quantity: Decimal
    gross_traded_value: Decimal
    total_fees: Decimal


class TransactionAnalyticsCurrencyResponse(BaseModel):
    currency: str
    transaction_count: int
    gross_traded_value: Decimal
    total_fees: Decimal


class TransactionAnalyticsBreakdownResponse(BaseModel):
    by_asset: list[TransactionAnalyticsAssetResponse]
    by_currency: list[TransactionAnalyticsCurrencyResponse]


class TransactionAnalyticsResponse(BaseModel):
    portfolio_id: int
    start_date: date | None
    end_date: date | None
    transaction_count: int
    breakdown: TransactionAnalyticsBreakdownResponse


class TransactionAnalyticsFilters(BaseModel):
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_date_range(self):
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError("start_date must be on or before end_date")

        return self


class TransactionCreate(BaseModel):
    asset_id: int = Field(gt=0)

    transaction_type: Literal["buy", "sell"]

    quantity: Decimal = Field(gt=0)

    price: Decimal = Field(gt=0)

    fees: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
    )

    transaction_date: date


class TransactionResponse(TransactionCreate):
    id: int
    portfolio_id: int

    model_config = ConfigDict(from_attributes=True)


class TransactionImportAssetSummary(BaseModel):
    asset_id: int
    transaction_count: int
    net_quantity: Decimal
    gross_traded_value: Decimal
    total_fees: Decimal


class TransactionImportResponse(BaseModel):
    imported_count: int
    transactions: list[TransactionResponse]
    summary: list[TransactionImportAssetSummary]


class TransactionUpdate(BaseModel):
    asset_id: int | None = Field(
        default=None,
        gt=0,
    )

    transaction_type: Literal["buy", "sell"] | None = None

    quantity: Decimal | None = Field(
        default=None,
        gt=0,
    )

    price: Decimal | None = Field(
        default=None,
        gt=0,
    )

    fees: Decimal | None = Field(
        default=None,
        ge=0,
    )

    transaction_date: date | None = None

    @field_validator(
        "asset_id",
        "transaction_type",
        "quantity",
        "price",
        "fees",
        "transaction_date",
        mode="before",
    )
    @classmethod
    def reject_null_values(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")

        return value


# --------------------------------------------------
# Holding and valuation schemas
# --------------------------------------------------


class HoldingResponse(BaseModel):
    asset_id: int
    symbol: str
    currency: str
    quantity: Decimal


class PortfolioSummaryResponse(BaseModel):
    portfolio_id: int
    name: str
    starting_cash: Decimal
    cash_balance: Decimal
    holdings: list[HoldingResponse]


# --------------------------------------------------
# Asset price schemas
# --------------------------------------------------


class AssetPriceCreate(BaseModel):
    price: Decimal = Field(gt=0)


class AssetPriceResponse(AssetPriceCreate):
    id: int
    asset_id: int
    priced_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------
# Portfolio valuation schemas
# --------------------------------------------------


class HoldingValuationResponse(HoldingResponse):
    latest_price: Decimal
    market_value: Decimal


class PortfolioValuationResponse(BaseModel):
    portfolio_id: int
    base_currency: str
    cash_balance: Decimal
    holdings_value: Decimal
    total_value: Decimal
    holdings: list[HoldingValuationResponse]
