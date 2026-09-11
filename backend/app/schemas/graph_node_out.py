"""Response schema for one node in a graph's topology."""

from typing import Literal

from pydantic import BaseModel


class GraphNodeOut(BaseModel):
    """One node of a compiled LangGraph, as introspected at request time."""

    id: str
    label: str
    kind: Literal["start", "end", "error_handler", "node"]
