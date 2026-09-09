"""Chat endpoint: SSE streaming answers, plus an availability check."""

import logging
import uuid
from collections.abc import Iterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps import ChatServiceDep
from app.api.sse import format_sse
from app.domain.exceptions import ChatUnavailableError
from app.schemas.chat_request import ChatRequest
from app.schemas.chat_status_out import ChatStatusOut
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def _sse_frames(service: ChatService, *, message: str, thread_id: str) -> Iterator[str]:
    """Frame the agent's tokens as SSE: zero or more `token`, then `done`.

    Lives in the API layer because SSE is a transport format; the service below
    yields plain text and stays unaware of how it reaches a browser.

    Deliberately not a try/finally: if the client disconnects mid-stream Python
    throws GeneratorExit in here, and a generator that yields after catching it
    raises RuntimeError. `done` sits after the try/except so it is skipped on
    that path and still emitted on every other one.
    """
    try:
        for token in service.stream_tokens(message=message, thread_id=thread_id):
            yield format_sse("token", {"text": token})
    except Exception:
        # Headers are already flushed by the time this generator runs, so a 5xx
        # is impossible here. Log the cause; tell the client nothing about our
        # internals.
        logger.exception("chat_stream_failed")
        yield format_sse("error", {"detail": "The answer could not be completed."})
    yield format_sse("done", {})


@router.get(
    "/status",
    response_model=ChatStatusOut,
    summary="Whether the chat agent is available",
    description="Lets the panel render a disabled state before anyone types a message.",
)
def get_chat_status(service: ChatServiceDep) -> ChatStatusOut:
    """Report whether a model is configured."""
    return ChatStatusOut(available=service.is_available())


@router.post(
    "",
    summary="Ask the chat agent a question, streamed",
    description=(
        "A POST, not an EventSource GET: a GET would put the person's question "
        "in the URL and every access log. `thread_id` is the entire memory "
        "mechanism - trusted as given, with no ownership check, the same trust "
        "boundary as the rest of this single-user, loopback-only application."
    ),
)
def post_chat(service: ChatServiceDep, body: ChatRequest) -> StreamingResponse:
    """Stream the answer as SSE: zero or more `token` events, then `done`.

    Availability is checked *before* the stream opens, so an unconfigured
    model is a clean 503 rather than a stream that starts and then breaks.

    Raises:
        ChatUnavailableError: If no chat model is configured.
    """
    if not service.is_available():
        raise ChatUnavailableError("no chat model is configured")

    thread_id = body.thread_id or str(uuid.uuid4())
    return StreamingResponse(
        _sse_frames(service, message=body.message, thread_id=thread_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
