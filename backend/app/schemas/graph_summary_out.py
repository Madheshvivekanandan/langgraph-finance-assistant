"""Response schema for one graph's summary entry in a collection listing."""

from pydantic import BaseModel


class GraphSummaryOut(BaseModel):
    """Enough to list a registered graph without paying for full introspection."""

    name: str
    title: str
    node_count: int
