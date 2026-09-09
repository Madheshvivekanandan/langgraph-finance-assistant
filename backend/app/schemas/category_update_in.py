"""Request body for recategorizing a transaction."""

from pydantic import BaseModel, ConfigDict

from app.domain.transaction_category import TransactionCategory


class CategoryUpdateIn(BaseModel):
    """The category a person chose.

    Typed as the enum, so an unknown value is rejected by validation before any
    handler runs. extra="forbid" so a typo'd field is an error, not a silent no-op.
    """

    model_config = ConfigDict(extra="forbid")

    category: TransactionCategory
