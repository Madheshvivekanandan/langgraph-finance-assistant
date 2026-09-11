"""API tests for discarding a statement stuck AWAITING_REVIEW.

CI runs with no OPENAI_API_KEY, so the app's own statement graph never pauses.
These tests override `app.state.statement_graph` with one built over a
low-confidence stub and a real checkpointer, exactly as
`test_statement_review_api.py` does.
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

_UNMATCHED_CSV = b"Date,Description,Amount\n01/07/2026,UPI-KRISHNASAMY K-ZIONMOTORS,-6000.00\n"


class _LowConfidenceStubSuggester:
    def suggest(self, transactions: list[ParsedTransaction]) -> dict[int, CategoryPrediction]:
        return {
            index: CategoryPrediction(TransactionCategory.DINING, Decimal("0.30"))
            for index in range(len(transactions))
        }


def test_discard_a_paused_statement_then_second_delete_is_404(
    session_factory: sessionmaker[Session], statement_checkpointer: PostgresSaver
) -> None:
    with TestClient(create_app()) as client:
        client.app.state.statement_graph = build_statement_graph(
            session_factory, _LowConfidenceStubSuggester(), checkpointer=statement_checkpointer
        )

        upload = client.post(
            "/api/v1/statements",
            files={"file": ("discard.csv", _UNMATCHED_CSV, "text/csv")},
        )
        assert upload.status_code == 201
        statement_id = upload.json()["id"]
        assert upload.json()["status"] == "AWAITING_REVIEW"

        discard = client.delete(f"/api/v1/statements/{statement_id}")
        assert discard.status_code == 204
        assert discard.content == b""

        listing = client.get("/api/v1/statements")
        assert statement_id not in [item["id"] for item in listing.json()["items"]]

        second_discard = client.delete(f"/api/v1/statements/{statement_id}")
        assert second_discard.status_code == 404
        assert second_discard.json()["code"] == "STATEMENT_NOT_FOUND"


def test_reupload_after_discard_succeeds(
    session_factory: sessionmaker[Session], statement_checkpointer: PostgresSaver
) -> None:
    """The feature's whole point: discard frees the UNIQUE file_hash for re-upload."""
    with TestClient(create_app()) as client:
        client.app.state.statement_graph = build_statement_graph(
            session_factory, _LowConfidenceStubSuggester(), checkpointer=statement_checkpointer
        )

        first_upload = client.post(
            "/api/v1/statements",
            files={"file": ("discard.csv", _UNMATCHED_CSV, "text/csv")},
        )
        assert first_upload.status_code == 201
        first_statement_id = first_upload.json()["id"]

        discard = client.delete(f"/api/v1/statements/{first_statement_id}")
        assert discard.status_code == 204

        second_upload = client.post(
            "/api/v1/statements",
            files={"file": ("discard.csv", _UNMATCHED_CSV, "text/csv")},
        )
        assert second_upload.status_code == 201
        second_body = second_upload.json()
        assert second_body["status"] == "AWAITING_REVIEW"
        assert second_body["id"] != first_statement_id


def test_discard_unknown_statement_is_404(client: TestClient) -> None:
    response = client.delete("/api/v1/statements/999999")

    assert response.status_code == 404
    assert response.json()["code"] == "STATEMENT_NOT_FOUND"
    assert response.headers["content-type"].startswith("application/problem+json")


def test_discard_a_completed_statement_is_409(client: TestClient) -> None:
    """Uses the shared `client` fixture, whose suggester answers above the review threshold."""
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
    assert upload.json()["status"] == "COMPLETED"

    response = client.delete(f"/api/v1/statements/{statement_id}")

    assert response.status_code == 409
    assert response.json()["code"] == "STATEMENT_NOT_AWAITING_REVIEW"
