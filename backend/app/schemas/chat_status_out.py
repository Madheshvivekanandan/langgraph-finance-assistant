"""Response schema for whether the chat agent is available."""

from pydantic import BaseModel


class ChatStatusOut(BaseModel):
    """Lets the frontend render a disabled state before anyone types a message."""

    available: bool
