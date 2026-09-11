"""Response schema for one edge in a graph's topology."""

from pydantic import BaseModel


class GraphEdgeOut(BaseModel):
    """One edge of a compiled LangGraph, as introspected at request time."""

    source: str
    target: str
    conditional: bool
    label: str | None = None
