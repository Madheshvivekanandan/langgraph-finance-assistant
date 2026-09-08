"""Unit tests for the statement graph's conditional edges."""

from app.graphs.statement.routing import route_after_normalize, route_after_parse


def test_route_after_parse_continues_when_no_error() -> None:
    assert route_after_parse({"rows": []}) == "normalize_rows"


def test_route_after_parse_diverts_to_failure_when_error_present() -> None:
    assert route_after_parse({"error": "bad header"}) == "record_failure"


def test_route_after_normalize_continues_when_no_error() -> None:
    assert route_after_normalize({"transactions": []}) == "store_transactions"


def test_route_after_normalize_diverts_to_failure_when_error_present() -> None:
    assert route_after_normalize({"error": "nothing readable"}) == "record_failure"


def test_routers_treat_an_empty_error_string_as_no_error() -> None:
    # Guards against a node returning error="" and silently failing the run.
    assert route_after_parse({"error": ""}) == "normalize_rows"
