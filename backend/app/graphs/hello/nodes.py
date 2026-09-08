"""Nodes for the hello graph. Each node returns a partial state update."""

from app.graphs.hello.state import HelloState


def compose_greeting(state: HelloState) -> dict[str, str]:
    """Turn the input name into a greeting."""
    name = state.get("name", "stranger")
    return {"greeting": f"Hello, {name}!"}


def add_welcome(state: HelloState) -> dict[str, str]:
    """Append the app welcome line to the greeting."""
    return {"greeting": state["greeting"] + " Welcome to My Finance."}
