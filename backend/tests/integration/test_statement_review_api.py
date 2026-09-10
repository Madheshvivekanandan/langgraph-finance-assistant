"""API tests for the statement review endpoints.

CI runs with no OPENAI_API_KEY, so the app's own statement graph never pauses.
Every test here overrides `app.state.statement_graph` with one built over a
low-confidence stub and a real checkpointer, exactly as
`tests/integration/test_chat_route.py` overrides `app.state.chat_agent`.
"""

from decimal import Decimal

from fastapi.testclient import TestClient
from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy.orm import Session, sessionmaker

from app.domain.category_prediction import CategoryPrediction
from app.domain.parsed_transaction import ParsedTransaction
from app.domain.transaction_category import TransactionCategory
from app.graphs.statement.graph import build_statement_graph
from app.main import create_app

_UNMATCHED_CSV = (
    b"Date,Description,Amount\n"
    b"01/07/2026,UPI-KRISHNASAMY K-ZIONMOTORS,-6000.00\n"
    b"02/07/2026,UPI-RAMASAMY R-XYZTRADERS,-1200.00\n"
)


class _LowConfidenceStubSuggester:
    def suggest(self, transactions: list[ParsedTransaction]) -> dict[int, CategoryPrediction]:
        return {
            index: CategoryPrediction(TransactionCategory.DINING, Decimal("0.30"))
            for index in range(len(transactions))
        }


def test_upload_review_and_resume_round_trip(
    session_factory: sessionmaker[Session], statement_checkpointer: PostgresSaver
) -> None:
    with TestClient(create_app()) as client:
        client.app.state.statement_graph = build_statement_graph(
            session_factory, _LowConfidenceStubSuggester(), checkpointer=statement_checkpointer
        )

        upload = client.post(
            "/api/v1/statements",
            files={"file": ("review.csv", _UNMATCHED_CSV, "text/csv")},
        )
        assert upload.status_code == 201
        body = upload.json()
        assert body["status"] == "AWAITING_REVIEW"
        assert body["transaction_count"] == 0
        statement_id = body["id"]

        pending = client.get(f"/api/v1/statements/{statement_id}/review")
        assert pending.status_code == 200
        pending_body = pending.json()
        assert pending_body["statement_id"] == statement_id
        assert pending_body["threshold"] == "0.75"
        assert [item["index"] for item in pending_body["items"]] == [0, 1]
        assert pending_body["items"][0]["amount"] == "6000.00"

        resolved = client.post(
            f"/api/v1/statements/{statement_id}/review",
            json={"decisions": [{"index": 0, "category": "GROCERIES"}]},
        )
        assert resolved.status_code == 200
        resolved_body = resolved.json()
        assert resolved_body["status"] == "COMPLETED"
        assert resolved_body["transaction_count"] == 2

        second_submit = client.post(
            f"/api/v1/statements/{statement_id}/review",
            json={"decisions": []},
        )
        assert second_submit.status_code == 409
        assert second_submit.headers["content-type"].startswith("application/problem+json")
        assert second_submit.json()["code"] == "STATEMENT_NOT_AWAITING_REVIEW"


def test_get_review_for_unknown_statement_is_404(
    session_factory: sessionmaker[Session], statement_checkpointer: PostgresSaver
) -> None:
    with TestClient(create_app()) as client:
        client.app.state.statement_graph = build_statement_graph(
            session_factory, _LowConfidenceStubSuggester(), checkpointer=statement_checkpointer
        )

        response = client.get("/api/v1/statements/999999/review")

    assert response.status_code == 404
    assert response.json()["code"] == "STATEMENT_NOT_FOUND"


def test_get_review_for_a_completed_statement_is_409(client: TestClient) -> None:
    """A statement that never paused has no review to fetch.

    Uses the shared `client` fixture, whose suggester answers above the review
    threshold, so this run completes whether or not a keyword rule matched.
    """
    upload = client.post(
        "/api/v1/statements",
        files={
            "file": (
                "july.csv",
                b"Date,Description,Amount\n01/07/2026,SWIGGY ORDER,-450.00\n",
                "text/csv",
            )
        },
    )
    statement_id = upload.json()["id"]

    response = client.get(f"/api/v1/statements/{statement_id}/review")

    assert response.status_code == 409
    assert response.json()["code"] == "STATEMENT_NOT_AWAITING_REVIEW"
