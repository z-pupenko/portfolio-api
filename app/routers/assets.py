from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Asset, AssetPrice, User
from app.routers.lookups import get_asset_or_404
from app.schemas import (
    AssetCreate,
    AssetPriceCreate,
    AssetPriceResponse,
    AssetResponse,
)

router = APIRouter(
    prefix="/assets",
    tags=["Assets"],
)
# --------------------------------------------------
# Basic asset operations
# --------------------------------------------------


@router.post(
    "/",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_asset(
    asset_data: AssetCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> Asset:
    symbol = asset_data.symbol.strip().upper()

    existing_asset = db.scalar(select(Asset).where(Asset.symbol == symbol))

    if existing_asset is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An asset with this symbol already exists",
        )

    asset = Asset(
        symbol=symbol,
        name=asset_data.name.strip(),
        asset_type=asset_data.asset_type.strip().lower(),
        currency=asset_data.currency.strip().upper(),
    )

    db.add(asset)
    db.commit()
    db.refresh(asset)

    return asset


@router.get(
    "/",
    response_model=list[AssetResponse],
)
def get_assets(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> list[Asset]:
    statement = select(Asset).order_by(Asset.symbol)

    return db.scalars(statement).all()


# --------------------------------------------------
# Asset prices
# --------------------------------------------------


@router.post(
    "/{asset_id}/prices/",
    response_model=AssetPriceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_asset_price(
    asset_id: int,
    price_data: AssetPriceCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> AssetPrice:
    get_asset_or_404(
        db,
        asset_id,
    )

    asset_price = AssetPrice(
        asset_id=asset_id,
        price=price_data.price,
    )

    db.add(asset_price)
    db.commit()
    db.refresh(asset_price)

    return asset_price


@router.get(
    "/{asset_id}/prices/latest/",
    response_model=AssetPriceResponse,
)
def get_latest_asset_price(
    asset_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> AssetPrice:
    get_asset_or_404(
        db,
        asset_id,
    )

    statement = (
        select(AssetPrice)
        .where(AssetPrice.asset_id == asset_id)
        .order_by(
            AssetPrice.priced_at.desc(),
            AssetPrice.id.desc(),
        )
        .limit(1)
    )

    latest_price = db.scalar(statement)

    if latest_price is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No price found for this asset",
        )

    return latest_price
