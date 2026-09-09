"""Server-sent event framing for the chat stream."""

import json
from typing import Any


def format_sse(event: str, data: dict[str, Any]) -> str:
    """Format one SSE frame: an `event:` line, a JSON `data:` line, a blank line.

    The payload is always JSON-encoded, never raw text: a token containing a
    literal newline written raw would terminate the SSE frame early and
    silently corrupt the stream. `json.dumps` guarantees the payload is exactly
    one line.
    """
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
