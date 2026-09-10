"""The statement ingestion graph.

    START -> create_statement -> parse_csv -> normalize_rows -> apply_category_rules
                                     |              |                      |
                                     |              |        (all matched) |  (some left)
                                     |              |                      v         v
                                     |              |     store_transactions <- categorize_with_llm
                                     |              |                ^
                                     |              |     review_low_confidence
                                     |              |                ^
                                     |              |     mark_awaiting_review
                                     +--------------+--> record_failure -> END

Both conditional edges after parse/normalize route to `record_failure` whenever
a node has put an `error` in state. Expected failures (bad headers, unreadable
rows) travel as state; unexpected ones (a dropped database connection) are
raised and retried.

`categorize_with_llm` has a third conditional edge, `route_after_llm`: with
nothing flagged low-confidence it goes straight to `store_transactions`, same
as before; otherwise it goes to `mark_awaiting_review -> review_low_confidence`
(which may suspend the whole run via `interrupt()`) before rejoining
`store_transactions`.
"""

from functools import partial
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import RetryPolicy
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.clients.category_suggester_factory import build_category_suggester
from app.db.session import get_session_factory
from app.domain.category_suggester import CategorySuggester
from app.domain.low_confidence_policy import LowConfidencePolicy
from app.graphs.statement.graph_input import StatementGraphInput
from app.graphs.statement.nodes.apply_category_rules import apply_category_rules
from app.graphs.statement.nodes.categorize_with_llm_node import CategorizeWithLlmNode
from app.graphs.statement.nodes.create_statement_node import CreateStatementNode
from app.graphs.statement.nodes.mark_awaiting_review_node import MarkAwaitingReviewNode
from app.graphs.statement.nodes.normalize_rows import normalize_rows
from app.graphs.statement.nodes.parse_csv import parse_csv
from app.graphs.statement.nodes.record_failure_node import RecordFailureNode
from app.graphs.statement.nodes.record_unexpected_failure_node import (
    RecordUnexpectedFailureNode,
)
from app.graphs.statement.nodes.review_low_confidence_node import ReviewLowConfidenceNode
from app.graphs.statement.nodes.store_transactions_node import StoreTransactionsNode
from app.graphs.statement.routing import (
    route_after_llm,
    route_after_normalize,
    route_after_parse,
    route_after_rules,
)
from app.graphs.statement.state import StatementState


def build_statement_graph(
    session_factory: sessionmaker[Session],
    category_suggester: CategorySuggester | None = None,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> CompiledStateGraph[StatementState]:
    """Wire up the ingestion pipeline.

    Args:
        session_factory: Injected so tests can run the graph against a
            throwaway database.
        category_suggester: Fills in categories no keyword rule matched. None
            disables the model step; ingestion still succeeds.
        checkpointer: Enables `interrupt()` in `review_low_confidence` to
            actually suspend the run rather than raise. None compiles a graph
            that can never pause - see the module-level `graph` below.
    """
    # arg-type: LangGraph types `input_schema` as the state schema itself, but the
    # runtime explicitly supports a narrower input schema - which is the point here.
    builder: StateGraph[StatementState] = StateGraph(
        StatementState,
        input_schema=StatementGraphInput,  # type: ignore[arg-type]
    )

    builder.add_node("create_statement", CreateStatementNode(session_factory))
    # parse_csv and normalize_rows convert their own faults into `error` state,
    # so the conditional edges below carry them to record_failure and the whole
    # failure path stays drawn in the graph.
    builder.add_node("parse_csv", parse_csv)
    builder.add_node("normalize_rows", normalize_rows)
    builder.add_node(
        "store_transactions",
        StoreTransactionsNode(session_factory),
        # Only a genuinely transient fault is worth repeating. An IntegrityError
        # would fail identically every time, so it is deliberately not retried.
        retry_policy=RetryPolicy(max_attempts=3, retry_on=OperationalError),
        # The one node that cannot report through state. A retry policy only
        # fires on an exception that escapes the node, so this one must raise -
        # and a raised failure has no state for a router to read. The handler is
        # the runtime's answer; it appears in the diagram as a detached
        # __error_handler__ node because it is reached by an exception, not an edge.
        error_handler=RecordUnexpectedFailureNode(session_factory),
    )
    builder.add_node("apply_category_rules", apply_category_rules)
    builder.add_node("categorize_with_llm", CategorizeWithLlmNode(category_suggester))
    builder.add_node("record_failure", RecordFailureNode(session_factory))

    # One shared policy instance, bound into both the router and the node, so
    # "low confidence" has a single definition (D4).
    low_confidence_policy = LowConfidencePolicy()
    builder.add_node("mark_awaiting_review", MarkAwaitingReviewNode(session_factory))
    builder.add_node("review_low_confidence", ReviewLowConfidenceNode(low_confidence_policy))

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
        {
            "apply_category_rules": "apply_category_rules",
            "record_failure": "record_failure",
        },
    )
    builder.add_conditional_edges(
        "apply_category_rules",
        route_after_rules,
        {
            "categorize_with_llm": "categorize_with_llm",
            "store_transactions": "store_transactions",
        },
    )
    builder.add_conditional_edges(
        "categorize_with_llm",
        partial(route_after_llm, policy=low_confidence_policy),
        {
            "mark_awaiting_review": "mark_awaiting_review",
            "store_transactions": "store_transactions",
        },
    )
    builder.add_edge("mark_awaiting_review", "review_low_confidence")
    builder.add_edge("review_low_confidence", "store_transactions")
    builder.add_edge("store_transactions", END)
    builder.add_edge("record_failure", END)

    return builder.compile(checkpointer=checkpointer)


# Module-level instance so langgraph.json (and therefore LangGraph Studio) points
# at exactly the graph the API runs.
graph = build_statement_graph(get_session_factory(), build_category_suggester())
