"""Builds the category suggester, or nothing when no key is configured."""

import logging

from app.clients.openai_api_key import resolve_openai_api_key
from app.clients.openai_category_suggester import OpenAiCategorySuggester
from app.core.config import get_settings
from app.domain.category_suggester import CategorySuggester

logger = logging.getLogger(__name__)


def build_category_suggester() -> CategorySuggester | None:
    """Return an OpenAI-backed suggester, or None if no usable key is set.

    Returning None rather than raising is deliberate: the app must run, and
    statements must still ingest, before anyone has added a key. Those rows just
    stay UNCATEGORIZED until one is configured.
    """
    settings = get_settings()
    api_key = resolve_openai_api_key()

    if api_key is None:
        logger.warning(
            "llm_categorization_disabled",
            extra={"reason": "OPENAI_API_KEY is missing or a placeholder"},
        )
        return None

    logger.info("llm_categorization_enabled", extra={"llm_model": settings.openai_model})
    return OpenAiCategorySuggester(api_key=api_key, model=settings.openai_model)
