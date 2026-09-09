"""Unit tests for the SSE framing helper."""

import json

from app.api.sse import format_sse


def test_format_sse_produces_the_event_and_json_data_lines() -> None:
    frame = format_sse("token", {"text": "hello"})

    assert frame == 'event: token\ndata: {"text": "hello"}\n\n'


def test_format_sse_ends_with_a_blank_line() -> None:
    frame = format_sse("done", {})

    assert frame.endswith("\n\n")


def test_a_token_containing_a_newline_survives_the_round_trip() -> None:
    """The single most likely bug: a raw newline would terminate the frame early."""
    frame = format_sse("token", {"text": "line one\nline two"})

    # Exactly one data: line - the newline lives safely inside the JSON string.
    data_lines = [line for line in frame.split("\n") if line.startswith("data: ")]
    assert len(data_lines) == 1
    payload = json.loads(data_lines[0][len("data: ") :])
    assert payload["text"] == "line one\nline two"


def test_format_sse_escapes_arbitrary_control_characters() -> None:
    frame = format_sse("token", {"text": "a\r\nb\tc"})

    data_line = next(line for line in frame.split("\n") if line.startswith("data: "))
    assert json.loads(data_line[len("data: ") :])["text"] == "a\r\nb\tc"
