"""Use case: introspect a compiled LangGraph's topology for the graph-view UI."""

from typing import Any, Literal

from langgraph.graph.state import CompiledStateGraph

from app.domain.exceptions import GraphNotFoundError
from app.graphs.statement.graph import graph as statement_graph
from app.schemas.graph_edge_out import GraphEdgeOut
from app.schemas.graph_list_out import GraphListOut
from app.schemas.graph_node_out import GraphNodeOut
from app.schemas.graph_summary_out import GraphSummaryOut
from app.schemas.graph_topology_out import GraphTopologyOut

_ERROR_HANDLER_PREFIX = "__error_handler__"

# Module-level registry: name -> (title, the compiled graph the API actually runs).
# Only the statement graph is exposed - the chat graph is deliberately excluded
# (see docs/PLAN.md and the route docstring): it needs a chat model to build and
# this app must boot with none configured. Adding it later is one entry here,
# not a contract change, which is the reason `GraphListOut` exists at all.
_REGISTRY: dict[str, tuple[str, CompiledStateGraph[Any, Any, Any, Any]]] = {
    "statement": ("Statement ingestion pipeline", statement_graph),
}


def _node_kind(node_id: str) -> Literal["start", "end", "error_handler", "node"]:
    """Classify a node id the same way LangGraph itself distinguishes them."""
    if node_id == "__start__":
        return "start"
    if node_id == "__end__":
        return "end"
    if node_id.startswith(_ERROR_HANDLER_PREFIX):
        return "error_handler"
    return "node"


class GraphTopologyService:
    """Reads topology straight off a compiled graph, never from a checked-in copy.

    A checked-in diagram is correct exactly once; introspecting the live object
    costs one function call and cannot drift from the pipeline it depicts.
    """

    def list_graphs(self) -> GraphListOut:
        """List every registered graph with a cheap summary, no full introspection."""
        summaries = [
            GraphSummaryOut(
                name=name,
                title=title,
                node_count=len(compiled.get_graph().nodes),
            )
            for name, (title, compiled) in _REGISTRY.items()
        ]
        return GraphListOut(graphs=summaries)

    def get_topology(self, name: str) -> GraphTopologyOut:
        """Return one graph's full topology, including its mermaid source.

        Raises:
            GraphNotFoundError: If no graph is registered under `name`.
        """
        entry = _REGISTRY.get(name)
        if entry is None:
            raise GraphNotFoundError(name)
        title, compiled = entry

        drawable = compiled.get_graph()
        nodes = [
            GraphNodeOut(id=node.id, label=node.name, kind=_node_kind(node.id))
            for node in drawable.nodes.values()
        ]
        edges = [
            GraphEdgeOut(
                source=edge.source,
                target=edge.target,
                conditional=edge.conditional,
                label=str(edge.data) if edge.data is not None else None,
            )
            for edge in drawable.edges
        ]
        return GraphTopologyOut(
            name=name,
            title=title,
            nodes=nodes,
            edges=edges,
            mermaid=drawable.draw_mermaid(),
        )
