"""API tests for the graph topology introspection endpoints."""

from fastapi.testclient import TestClient

_EXPECTED_STATEMENT_NODES = {
    "__start__",
    "__end__",
    "create_statement",
    "parse_csv",
    "normalize_rows",
    "apply_category_rules",
    "categorize_with_llm",
    "mark_awaiting_review",
    "review_low_confidence",
    "store_transactions",
    "record_failure",
}


def test_list_graphs_returns_statement(client: TestClient) -> None:
    response = client.get("/api/v1/graphs")

    assert response.status_code == 200
    body = response.json()
    assert len(body["graphs"]) == 1
    assert body["graphs"][0]["name"] == "statement"
    assert body["graphs"][0]["node_count"] > 0


def test_statement_topology_contains_every_pipeline_node(client: TestClient) -> None:
    response = client.get("/api/v1/graphs/statement")

    assert response.status_code == 200
    body = response.json()
    node_ids = {node["id"] for node in body["nodes"]}
    # Superset, not equality: adding a node to the pipeline must not fail this
    # test spuriously, but removing one - the drift this endpoint exists to
    # prevent - must.
    assert node_ids >= _EXPECTED_STATEMENT_NODES


def test_every_edge_endpoint_is_a_declared_node(client: TestClient) -> None:
    response = client.get("/api/v1/graphs/statement")

    assert response.status_code == 200
    body = response.json()
    node_ids = {node["id"] for node in body["nodes"]}
    edges = body["edges"]

    for edge in edges:
        assert edge["source"] in node_ids
        assert edge["target"] in node_ids
    assert any(edge["conditional"] for edge in edges)

    assert body["mermaid"]
    assert "graph TD" in body["mermaid"]
    assert "store_transactions" in body["mermaid"]


def test_unknown_graph_is_404_problem_json(client: TestClient) -> None:
    response = client.get("/api/v1/graphs/nope")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "GRAPH_NOT_FOUND"
