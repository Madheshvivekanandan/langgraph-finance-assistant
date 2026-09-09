"""Shared check for whether a usable OpenAI API key is configured.

Extracted from `category_suggester_factory` so the chat model factory (D9) can
apply the exact same rule without duplicating it - one definition of "no key
configured" for both features that degrade gracefully without one.
"""

from pydantic import SecretStr

from app.core.config import get_settings

_MIN_KEY_LENGTH = 20


def resolve_openai_api_key() -> SecretStr | None:
    """Return the configured key, or None if it is missing or a placeholder.

    `.env.example` ships the literal placeholder "sk-...", so length matters as
    much as presence.
    """
    api_key = get_settings().openai_api_key
    raw_key = api_key.get_secret_value().strip() if api_key is not None else ""
    if api_key is None or not raw_key.startswith("sk-") or len(raw_key) < _MIN_KEY_LENGTH:
        return None
    return api_key
