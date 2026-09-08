"""Response schema for a list of statements."""

from pydantic import BaseModel

from app.schemas.statement_out import StatementOut


class StatementListOut(BaseModel):
    """Statements wrapped in an object, never a bare array, so it can grow fields."""

    items: list[StatementOut]
