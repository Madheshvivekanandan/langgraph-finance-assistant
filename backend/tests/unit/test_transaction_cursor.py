"""Unit tests for the pagination cursor."""

from datetime import date

import pytest

from app.domain.exceptions import InvalidPageTokenError
from app.services.transaction_cursor import TransactionCursor


def test_cursor_round_trips_through_its_token() -> None:
    cursor = TransactionCursor(transaction_date=date(2026, 7, 1), transaction_id=42)

    assert TransactionCursor.decode(cursor.encode()) == cursor


def test_cursor_token_is_url_safe_and_unpadded() -> None:
    token = TransactionCursor(transaction_date=date(2026, 7, 1), transaction_id=42).encode()

    assert "=" not in token
    assert "/" not in token
    assert "+" not in token


@pytest.mark.parametrize("token", ["not-base64!", "", "YWJj", "MjAyNi0wNy0wMTpub3RhbnVt"])
def test_decode_rejects_tokens_this_api_did_not_issue(token: str) -> None:
    with pytest.raises(InvalidPageTokenError):
        TransactionCursor.decode(token)
