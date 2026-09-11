"""Unit tests for GraphTopologyService's node classification and lookup."""

import pytest

from app.domain.exceptions import GraphNotFoundError
from app.services.graph_topology_service import GraphTopologyService, _node_kind


def test_node_kind_classification() -> None:
    assert _node_kind("__start__") == "start"
    assert _node_kind("__end__") == "end"
    assert _node_kind("__error_handler__store_transactions") == "error_handler"
    assert _node_kind("parse_csv") == "node"


def test_unknown_name_raises_graph_not_found() -> None:
    service = GraphTopologyService()

    with pytest.raises(GraphNotFoundError):
        service.get_topology("nope")
