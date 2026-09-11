"""Response schema for one graph's full topology."""

from pydantic import BaseModel

from app.schemas.graph_edge_out import GraphEdgeOut
from app.schemas.graph_node_out import GraphNodeOut


class GraphTopologyOut(BaseModel):
    """A graph's nodes and edges, plus the mermaid source that renders them.

    Both shapes are returned deliberately: `mermaid` is the render source and
    can never drift from the diagram, while `nodes`/`edges` keep the contract
    renderer-agnostic for a legend, a node count, or a future non-mermaid view.
    """

    name: str
    title: str
    nodes: list[GraphNodeOut]
    edges: list[GraphEdgeOut]
    mermaid: str
