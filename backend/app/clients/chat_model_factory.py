"""Builds the chat agent's model, or nothing when no key is configured."""

import logging

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.clients.openai_api_key import resolve_openai_api_key
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def build_chat_model() -> BaseChatModel | None:
    """Return an OpenAI chat model, or None if no usable key is set.

    Mirrors `build_category_suggester`: the app must start, and the rest of the
    API must keep working, before anyone has added a key. The chat feature is
    what goes without - `ChatService.is_available()` reports it, the route 503s.
    """
    settings = get_settings()
    api_key = resolve_openai_api_key()

    if api_key is None:
        logger.warning(
            "chat_agent_disabled",
            extra={"reason": "OPENAI_API_KEY is missing or a placeholder"},
        )
        return None

    logger.info("chat_agent_enabled", extra={"llm_model": settings.openai_model})
    return ChatOpenAI(model=settings.openai_model, api_key=api_key, temperature=0)
