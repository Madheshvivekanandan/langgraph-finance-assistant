"""State schema for the hello graph."""

from typing_extensions import TypedDict


class HelloState(TypedDict, total=False):
    """Flows through the hello graph.

    `name` is the input; `greeting` is produced by the nodes. total=False because
    the graph is invoked with only `name` present.
    """

    name: str
    greeting: str
