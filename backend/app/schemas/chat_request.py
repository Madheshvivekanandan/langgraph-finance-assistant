"""Request body for a chat turn."""

import uuid

from pydantic import BaseModel, ConfigDict, field_validator


class ChatRequest(BaseModel):
    """One message from the person, plus which conversation it belongs to.

    `thread_id` is the entire memory mechanism (see ChatService): absent, the
    route generates one; present, it must already be a UUID, or FastAPI's
    validation rejects the request with 422 before any agent code runs.
    """

    model_config = ConfigDict(extra="forbid")

    message: str
    thread_id: str | None = None

    @field_validator("message")
    @classmethod
    def _message_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank")
        return value

    @field_validator("thread_id")
    @classmethod
    def _thread_id_is_a_uuid(cls, value: str | None) -> str | None:
        if value is None:
            return None
        uuid.UUID(value)  # raises ValueError on anything that is not a UUID
        return value
