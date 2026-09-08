"""Lifecycle of an uploaded statement."""

from enum import StrEnum


class StatementStatus(StrEnum):
    """Where an uploaded statement is in the ingestion pipeline."""

    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
