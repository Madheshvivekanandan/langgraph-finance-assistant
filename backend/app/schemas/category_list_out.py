"""Response schema for the category list."""

from pydantic import BaseModel

from app.schemas.category_out import CategoryOut


class CategoryListOut(BaseModel):
    """Categories wrapped in an object, never a bare array, so it can grow fields."""

    items: list[CategoryOut]
