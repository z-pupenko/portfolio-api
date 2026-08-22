from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Portfolio, User
from app.routers.lookups import get_portfolio_or_404
from app.schemas import (
    HoldingResponse,
    PortfolioCreate,
    PortfolioResponse,
    PortfolioSummaryResponse,
    PortfolioUpdate,
    PortfolioValuationResponse,
    TransactionAnalyticsFilters,
    TransactionAnalyticsResponse,
)
from app.services.analytics import (
    build_transaction_analytics,
    fetch_transaction_analytics_rows,
)
from app.services.portfolios import (
    calculate_cash_balance,
    calculate_holdings,
    calculate_portfolio_valuation,
)

router = APIRouter(
    prefix="/portfolios",
    tags=["Portfolios"],
)
# --------------------------------------------------
# Basic portfolio CRUD
# --------------------------------------------------


@router.post(
    "/",
    response_model=PortfolioResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_portfolio(
    portfolio_data: PortfolioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Portfolio:
    portfolio_values = portfolio_data.model_dump()

    portfolio_values["base_currency"] = portfolio_values["base_currency"].upper()

    portfolio = Portfolio(
        user_id=current_user.id,
        **portfolio_values,
    )

    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)

    return portfolio


@router.get(
    "/",
    response_model=list[PortfolioResponse],
)
def get_portfolios(
    name: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Portfolio]:
    statement = (
        select(Portfolio)
        .where(Portfolio.user_id == current_user.id)
        .order_by(Portfolio.id)
    )

    if name is not None:
        statement = statement.where(Portfolio.name == name)

    portfolios = db.scalars(statement).all()

    return portfolios


@router.get(
    "/{portfolio_id}",
    response_model=PortfolioResponse,
)
def get_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Portfolio:
    return get_portfolio_or_404(
        db,
        portfolio_id,
        current_user.id,
    )


@router.patch(
    "/{portfolio_id}",
    response_model=PortfolioResponse,
)
def update_portfolio(
    portfolio_id: int,
    portfolio_data: PortfolioUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Portfolio:
    portfolio = get_portfolio_or_404(
        db,
        portfolio_id,
        current_user.id,
    )

    update_data = portfolio_data.model_dump(exclude_unset=True)

    if "base_currency" in update_data:
        base_currency = update_data["base_currency"]

        if base_currency is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Base currency cannot be null",
            )

        update_data["base_currency"] = base_currency.upper()

    for field, value in update_data.items():
        setattr(portfolio, field, value)

    db.commit()
    db.refresh(portfolio)

    return portfolio


@router.delete(
    "/{portfolio_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    portfolio = get_portfolio_or_404(
        db,
        portfolio_id,
        current_user.id,
    )

    db.delete(portfolio)
    db.commit()


# --------------------------------------------------
# Portfolio calculations
# --------------------------------------------------


@router.get(
    "/{portfolio_id}/holdings",
    response_model=list[HoldingResponse],
)
def get_portfolio_holdings(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[HoldingResponse]:
    get_portfolio_or_404(
        db,
        portfolio_id,
        current_user.id,
    )

    holdings = calculate_holdings(db, portfolio_id)

    return [HoldingResponse.model_validate(holding) for holding in holdings]


@router.get(
    "/{portfolio_id}/summary",
    response_model=PortfolioSummaryResponse,
)
def get_portfolio_summary(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortfolioSummaryResponse:
    portfolio = get_portfolio_or_404(
        db,
        portfolio_id,
        current_user.id,
    )

    cash_balance = calculate_cash_balance(
        db,
        portfolio,
    )

    holdings = calculate_holdings(
        db,
        portfolio_id,
    )

    return PortfolioSummaryResponse(
        portfolio_id=portfolio.id,
        name=portfolio.name,
        starting_cash=portfolio.starting_cash,
        cash_balance=cash_balance,
        holdings=holdings,
    )


@router.get(
    "/{portfolio_id}/valuation",
    response_model=PortfolioValuationResponse,
)
def get_portfolio_valuation(
    portfolio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortfolioValuationResponse:
    portfolio = get_portfolio_or_404(
        db,
        portfolio_id,
        current_user.id,
    )

    try:
        valuation = calculate_portfolio_valuation(db, portfolio)
        return PortfolioValuationResponse.model_validate(valuation)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error


@router.get(
    "/{portfolio_id}/transaction-summary",
    response_model=TransactionAnalyticsResponse,
)
def get_portfolio_transaction_summary(
    portfolio_id: int,
    filters: Annotated[
        TransactionAnalyticsFilters,
        Query(),
    ],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionAnalyticsResponse:
    get_portfolio_or_404(
        db,
        portfolio_id,
        current_user.id,
    )

    rows = fetch_transaction_analytics_rows(
        db,
        portfolio_id,
        filters,
    )

    report = build_transaction_analytics(
        rows,
        portfolio_id,
        filters,
    )

    return report
