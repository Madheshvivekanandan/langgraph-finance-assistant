"""Read-only introspection of this app's compiled LangGraph pipelines.

Modelled on the other read-only introspection route in this app,
`chat.py::get_chat_status`. A checked-in copy of a graph's shape is correct
exactly once - the next person who adds a node ships a diagram that lies. This
route reads `graph.get_graph()` at request time instead, so the picture in the
UI can never disagree with the pipeline it depicts.
"""

from fastapi import APIRouter

from app.api.deps import GraphTopologyServiceDep
from app.schemas.graph_list_out import GraphListOut
from app.schemas.graph_topology_out import GraphTopologyOut

router = APIRouter(prefix="/graphs", tags=["graphs"])


@router.get(
    "",
    response_model=GraphListOut,
    summary="List the graphs this app can show a topology for",
)
def list_graphs(service: GraphTopologyServiceDep) -> GraphListOut:
    """Return every registered graph's name, title, and node count."""
    return service.list_graphs()


@router.get(
    "/{graph_name}",
    response_model=GraphTopologyOut,
    summary="Get one graph's full topology, including its mermaid diagram",
    description="404 if no graph is registered under that name.",
)
def get_graph_topology(graph_name: str, service: GraphTopologyServiceDep) -> GraphTopologyOut:
    """Return one graph's nodes, edges, and mermaid source.

    Raises:
        GraphNotFoundError: If no such graph is registered.
    """
    return service.get_topology(graph_name)
