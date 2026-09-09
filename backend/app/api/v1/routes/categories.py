"""The category vocabulary the UI offers."""

from fastapi import APIRouter

from app.domain.transaction_category import TransactionCategory
from app.schemas.category_list_out import CategoryListOut
from app.schemas.category_out import CategoryOut

router = APIRouter(prefix="/categories", tags=["categories"])


def _label(category: TransactionCategory) -> str:
    """Turn GROCERIES into Groceries for display."""
    return category.value.replace("_", " ").title()


@router.get(
    "",
    response_model=CategoryListOut,
    summary="List assignable categories",
    description=(
        "Served from the backend so the UI cannot drift from the category set "
        "the rules, the model, and the database CHECK constraint share."
    ),
)
def list_categories() -> CategoryListOut:
    """Return every category a person may choose."""
    return CategoryListOut(
        items=[
            CategoryOut(code=category.value, label=_label(category))
            for category in TransactionCategory.assignable()
        ]
    )
