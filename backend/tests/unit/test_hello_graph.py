"""Unit tests for the hello graph."""

from app.graphs.hello.graph import graph


def test_hello_graph_greets_by_name() -> None:
    result = graph.invoke({"name": "Madhesh"})

    assert result["greeting"] == "Hello, Madhesh! Welcome to My Finance."


def test_hello_graph_without_name_uses_fallback() -> None:
    result = graph.invoke({})

    assert result["greeting"] == "Hello, stranger! Welcome to My Finance."
