"""Transaction listing endpoint."""

from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.deps import TransactionCategoryServiceDep, TransactionQueryServiceDep
from app.schemas.category_update_in import CategoryUpdateIn
from app.schemas.transaction_out import TransactionOut
from app.schemas.transaction_page_out import TransactionPageOut

router = APIRouter(prefix="/transactions", tags=["transactions"])

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


@router.get(
    "",
    response_model=TransactionPageOut,
    response_model_exclude_none=True,
    summary="List transactions, newest first",
    description=(
        "Keyset-paginated. Follow the `next` token until it is absent; a short "
        "page does not mean the end."
    ),
)
def list_transactions(
    service: TransactionQueryServiceDep,
    page_size: Annotated[
        int, Query(ge=1, description="Rows per page; capped at 200")
    ] = DEFAULT_PAGE_SIZE,
    page_token: Annotated[str | None, Query(description="Cursor from a previous page")] = None,
) -> TransactionPageOut:
    """Return one page of transactions.

    Raises:
        InvalidPageTokenError: If `page_token` was not issued by this API.
    """
    page = service.list_page(page_size=min(page_size, MAX_PAGE_SIZE), page_token=page_token)
    return TransactionPageOut(
        items=[TransactionOut.model_validate(item) for item in page.items],
        next=page.next_token,
    )


@router.put(
    "/{transaction_id}/category",
    response_model=TransactionOut,
    response_model_exclude_none=True,
    summary="Set a transaction's category",
    description=(
        "Records the category on a person's authority. The stored source becomes "
        "USER, so a later re-run will not overwrite the correction."
    ),
)
def set_transaction_category(
    service: TransactionCategoryServiceDep,
    body: CategoryUpdateIn,
    transaction_id: Annotated[int, Path(ge=1, description="Transaction to recategorize")],
) -> TransactionOut:
    """Override a transaction's category.

    PUT rather than PATCH: this replaces the whole category assignment, so it is
    idempotent and needs no patch-document format. No If-Match, because this is
    a single-user application with no concurrent writers.

    Raises:
        TransactionNotFoundError: If no such transaction exists.
    """
    transaction = service.set_category(transaction_id=transaction_id, category=body.category)
    return TransactionOut.model_validate(transaction)
