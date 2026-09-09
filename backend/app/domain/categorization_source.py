"""Who or what assigned a transaction's category."""

from enum import StrEnum


class CategorizationSource(StrEnum):
    """Provenance of a category, so a person's choice is never silently overwritten."""

    NONE = "NONE"
    RULE = "RULE"
    LLM = "LLM"
    USER = "USER"
