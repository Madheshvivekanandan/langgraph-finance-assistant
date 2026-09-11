"""Response schema for the list of introspectable graphs."""

from pydantic import BaseModel

from app.schemas.graph_summary_out import GraphSummaryOut


class GraphListOut(BaseModel):
    """Graphs wrapped in an object, never a bare array, so it can grow fields."""

    graphs: list[GraphSummaryOut]
