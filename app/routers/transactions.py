from os import SEEK_END

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Transaction
from app.routers.lookups import (
    get_asset_or_404,
    get_portfolio_or_404,
    get_transaction_or_404,
)
from app.schemas import (
    TransactionCreate,
    TransactionImportResponse,
    TransactionResponse,
    TransactionUpdate,
)
from app.services.transaction_imports import (
    TransactionCSVFormatError,
    TransactionCSVImportError,
    TransactionCSVValidationError,
    build_transaction_summary,
    import_transaction_batch,
    parse_transaction_csv,
)
from app.services.transactions import (
    TransactionRuleError,
    add_transaction,
    validate_sufficient_cash,
    validate_sufficient_quantity,
)

router = APIRouter(
    tags=["Transactions"],
)
MAX_TRANSACTION_CSV_SIZE_BYTES = 5 * 1024 * 1024

# --------------------------------------------------
# Upload validation
# --------------------------------------------------


def validate_transaction_csv_upload(
    file: UploadFile,
) -> None:
    if file.filename is None or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE),
            detail="Uploaded file must be a CSV",
        )

    file.file.seek(0, SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > MAX_TRANSACTION_CSV_SIZE_BYTES:
        raise HTTPException(
            status_code=(status.HTTP_413_CONTENT_TOO_LARGE),
            detail=("CSV file exceeds the 5 MiB upload limit"),
        )


# --------------------------------------------------
# Transaction CRUD
# --------------------------------------------------
@router.post(
    "/portfolios/{portfolio_id}/transactions/import/",
    response_model=TransactionImportResponse,
    status_code=status.HTTP_201_CREATED,
)
def import_transactions_csv(
    portfolio_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> TransactionImportResponse:
    portfolio = get_portfolio_or_404(
        db,
        portfolio_id,
    )

    validate_transaction_csv_upload(file)

    try:
        transaction_rows = parse_transaction_csv(file.file)
    except TransactionCSVValidationError as error:
        raise HTTPException(
            status_code=(status.HTTP_422_UNPROCESSABLE_CONTENT),
            detail={
                "message": str(error),
                "errors": error.errors,
            },
        ) from error
    except TransactionCSVFormatError as error:
        raise HTTPException(
            status_code=(status.HTTP_422_UNPROCESSABLE_CONTENT),
            detail=str(error),
        ) from error

    transaction_summary = build_transaction_summary(transaction_rows)

    try:
        imported_transactions = import_transaction_batch(
            db,
            portfolio,
            transaction_rows,
        )
    except TransactionCSVImportError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "row": error.row,
                "message": error.message,
            },
        ) from error

    return TransactionImportResponse(
        imported_count=len(imported_transactions),
        transactions=imported_transactions,
        summary=transaction_summary,
    )


@router.post(
    "/portfolios/{portfolio_id}/transactions/",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    portfolio_id: int,
    transaction_data: TransactionCreate,
    db: Session = Depends(get_db),
) -> Transaction:
    portfolio = get_portfolio_or_404(
        db,
        portfolio_id,
    )

    get_asset_or_404(
        db,
        transaction_data.asset_id,
    )

    try:
        transaction = add_transaction(
            db,
            portfolio,
            transaction_data,
        )
    except TransactionRuleError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    db.commit()
    db.refresh(transaction)

    return transaction


@router.get(
    "/transactions/{transaction_id}",
    response_model=TransactionResponse,
)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
) -> Transaction:
    return get_transaction_or_404(
        db,
        transaction_id,
    )


@router.delete(
    "/transactions/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
) -> None:
    transaction = get_transaction_or_404(
        db,
        transaction_id,
    )

    db.delete(transaction)
    db.commit()


@router.patch(
    "/transactions/{transaction_id}",
    response_model=TransactionResponse,
)
def update_transaction(
    transaction_id: int,
    transaction_data: TransactionUpdate,
    db: Session = Depends(get_db),
) -> Transaction:
    transaction = get_transaction_or_404(
        db,
        transaction_id,
    )

    update_data = transaction_data.model_dump(exclude_unset=True)

    proposed_asset_id = update_data.get(
        "asset_id",
        transaction.asset_id,
    )

    proposed_type = update_data.get(
        "transaction_type",
        transaction.transaction_type,
    )

    proposed_quantity = update_data.get(
        "quantity",
        transaction.quantity,
    )

    proposed_price = update_data.get(
        "price",
        transaction.price,
    )

    proposed_fees = update_data.get(
        "fees",
        transaction.fees,
    )

    get_asset_or_404(
        db,
        proposed_asset_id,
    )

    portfolio = get_portfolio_or_404(
        db,
        transaction.portfolio_id,
    )

    try:
        if proposed_type == "buy":
            validate_sufficient_cash(
                db,
                portfolio,
                proposed_quantity,
                proposed_price,
                proposed_fees,
                exclude_transaction_id=transaction.id,
            )
        elif proposed_type == "sell":
            validate_sufficient_quantity(
                db,
                transaction.portfolio_id,
                proposed_asset_id,
                proposed_quantity,
                exclude_transaction_id=transaction.id,
            )
        else:
            raise RuntimeError(f"Unsupported transaction type: {proposed_type}")
    except TransactionRuleError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    for field, value in update_data.items():
        setattr(transaction, field, value)

    db.commit()
    db.refresh(transaction)

    return transaction


# --------------------------------------------------
# Portfolio transaction listing
# --------------------------------------------------


@router.get(
    "/portfolios/{portfolio_id}/transactions/",
    response_model=list[TransactionResponse],
)
def get_portfolio_transactions(
    portfolio_id: int,
    db: Session = Depends(get_db),
) -> list[Transaction]:
    get_portfolio_or_404(
        db,
        portfolio_id,
    )

    statement = (
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.id)
    )

    transactions = db.scalars(statement).all()

    return transactions
