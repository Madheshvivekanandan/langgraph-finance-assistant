"""The statement ingestion graph.

    START -> create_statement -> parse_csv -> normalize_rows -> store_transactions -> END
                                     |              |
                                     +--------------+--> record_failure -> END

Both conditional edges route to `record_failure` whenever a node has put an
`error` in state. Expected failures (bad headers, unreadable rows) travel as
state; unexpected ones (a dropped database connection) are raised and retried.
"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import RetryPolicy
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import get_session_factory
from app.graphs.statement.graph_input import StatementGraphInput
from app.graphs.statement.nodes.create_statement_node import CreateStatementNode
from app.graphs.statement.nodes.normalize_rows import normalize_rows
from app.graphs.statement.nodes.parse_csv import parse_csv
from app.graphs.statement.nodes.record_failure_node import RecordFailureNode
from app.graphs.statement.nodes.store_transactions_node import StoreTransactionsNode
from app.graphs.statement.routing import route_after_normalize, route_after_parse
from app.graphs.statement.state import StatementState


def build_statement_graph(
    session_factory: sessionmaker[Session],
) -> CompiledStateGraph[StatementState]:
    """Wire up the ingestion pipeline.

    Args:
        session_factory: Injected so tests can run the graph against a
            throwaway database.
    """
    # arg-type: LangGraph types `input_schema` as the state schema itself, but the
    # runtime explicitly supports a narrower input schema - which is the point here.
    builder: StateGraph[StatementState] = StateGraph(
        StatementState,
        input_schema=StatementGraphInput,  # type: ignore[arg-type]
    )

    builder.add_node("create_statement", CreateStatementNode(session_factory))
    builder.add_node("parse_csv", parse_csv)
    builder.add_node("normalize_rows", normalize_rows)
    builder.add_node(
        "store_transactions",
        StoreTransactionsNode(session_factory),
        # Only a genuinely transient fault is worth repeating. An IntegrityError
        # would fail identically every time, so it is deliberately not retried.
        retry_policy=RetryPolicy(max_attempts=3, retry_on=OperationalError),
    )
    builder.add_node("record_failure", RecordFailureNode(session_factory))

    builder.add_edge(START, "create_statement")
    builder.add_edge("create_statement", "parse_csv")
    builder.add_conditional_edges(
        "parse_csv",
        route_after_parse,
        {"normalize_rows": "normalize_rows", "record_failure": "record_failure"},
    )
    builder.add_conditional_edges(
        "normalize_rows",
        route_after_normalize,
        {"store_transactions": "store_transactions", "record_failure": "record_failure"},
    )
    builder.add_edge("store_transactions", END)
    builder.add_edge("record_failure", END)

    return builder.compile()


# Module-level instance so langgraph.json (and therefore LangGraph Studio) points
# at exactly the graph the API runs.
graph = build_statement_graph(get_session_factory())
