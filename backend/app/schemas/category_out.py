"""Response schema for one selectable category."""

from pydantic import BaseModel


class CategoryOut(BaseModel):
    """A category the UI can offer, with a display label."""

    code: str
    label: str
