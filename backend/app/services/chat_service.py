"""Use case: stream an answer from the chat agent, with conversation memory."""

import logging
from collections.abc import Iterator
from typing import Any

from langchain_core.messages import AIMessageChunk, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from app.domain.exceptions import ChatUnavailableError

logger = logging.getLogger(__name__)


class ChatService:
    """Drives the chat agent and turns its token stream into SSE frames.

    Single-user, no auth: `thread_id` is trusted as given, same trust boundary
    as the rest of this application (loopback-only in compose).
    """

    def __init__(self, agent: CompiledStateGraph[Any, Any, Any, Any] | None) -> None:
        self._agent = agent

    def is_available(self) -> bool:
        """Whether a model is configured at all.

        The route checks this *before* returning a `StreamingResponse`, so an
        unavailable agent is a clean 503 rather than a stream that opens and
        then breaks.
        """
        return self._agent is not None

    def stream_tokens(self, *, message: str, thread_id: str) -> Iterator[str]:
        """Stream the answer as plain text tokens.

        Yields text, not wire frames: SSE is a transport concern and belongs in
        the API layer. A service that formatted its own frames would have to
        import from `app.api`, which inverts the dependency this codebase's
        layering rules exist to protect.

        Raises:
            ChatUnavailableError: If no model is configured.
        """
        if self._agent is None:
            raise ChatUnavailableError("no chat model is configured")

        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        for chunk, _metadata in self._agent.stream(
            {"messages": [HumanMessage(content=message)]},
            config=config,
            stream_mode="messages",
        ):
            if isinstance(chunk, AIMessageChunk) and chunk.content:
                yield str(chunk.content)
