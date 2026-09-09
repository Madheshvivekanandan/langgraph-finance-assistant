"""A scripted, call-recording chat model for testing the chat agent.

Not `GenericFakeChatModel`: `create_agent` calls `model.bind_tools(tools)`, and
the base class's `bind_tools` raises `NotImplementedError` by default - the
built-in fakes do not override it. This fake also records every message list it
was invoked with, which is what makes the cross-turn memory assertion possible.
"""

import re
from collections.abc import Iterator
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.chat_models import LanguageModelInput
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.runnables import Runnable
from pydantic import PrivateAttr


class FakeChatModel(BaseChatModel):
    """Pops one scripted `AIMessage` per invocation.

    `bind_tools` is a no-op returning `self`: `create_agent` binds tools before
    every call, and this fake ignores the schema and simply replays the script.
    """

    _responses: list[AIMessage] = PrivateAttr()
    _calls: list[list[BaseMessage]] = PrivateAttr(default_factory=list)

    def __init__(self, responses: list[AIMessage], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._responses = list(responses)
        self._calls = []

    @property
    def calls(self) -> list[list[BaseMessage]]:
        """Every message list this model was asked to respond to, in order."""
        return self._calls

    @property
    def _llm_type(self) -> str:
        return "fake-chat-model"

    def bind_tools(
        self,
        tools: Any,
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, AIMessage]:
        """Return self unchanged: the script already encodes any tool calls."""
        del tools, tool_choice, kwargs
        return self  # type: ignore[return-value]

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        del stop, run_manager, kwargs
        self._calls.append(list(messages))
        if not self._responses:
            raise AssertionError("FakeChatModel script exhausted - add another response")
        message = self._responses.pop(0)
        return ChatResult(generations=[ChatGeneration(message=message)])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        result = self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        message = result.generations[0].message

        content = message.content
        if not content:
            yield ChatGenerationChunk(
                message=AIMessageChunk(content="", tool_calls=message.tool_calls, id=message.id)
            )
            return

        # Split on whitespace, keeping it, so streaming looks token-by-token
        # rather than delivering the whole answer as one chunk.
        pieces = re.split(r"(\s)", str(content))
        for index, piece in enumerate(pieces):
            # Tool calls arrive on the final chunk only, mirroring a real
            # provider that emits them once content streaming is done.
            tool_calls = message.tool_calls if index == len(pieces) - 1 else []
            chunk = ChatGenerationChunk(
                message=AIMessageChunk(content=piece, tool_calls=tool_calls, id=message.id)
            )
            if run_manager:
                run_manager.on_llm_new_token(piece, chunk=chunk)
            yield chunk
