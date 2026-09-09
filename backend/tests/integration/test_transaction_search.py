"""Integration tests for TransactionRepository.search against a real database."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.domain.month import Month
from app.domain.transaction_category import TransactionCategory
from app.repositories.transaction_repository import TransactionRepository

_JULY_CSV = (
    b"Date,Description,Amount\n"
    b"01/07/2026,UPI-SWIGGY ORDER,-486.00\n"
    b"02/07/2026,SALARY CREDIT,85000.00\n"
    b"03/07/2026,UPI-BLINKIT GROCERY,-1000.00\n"
    b"04/07/2026,100% OFF DISCOUNT_CODE,-50.00\n"
)
_AUGUST_CSV = b"Date,Description,Amount\n05/08/2026,UPI-SWIGGY ORDER,-300.00\n"


def _upload(client: TestClient, content: bytes, name: str) -> None:
    response = client.post("/api/v1/statements", files={"file": (name, content, "text/csv")})
    assert response.status_code < 400


def test_search_matches_substring_case_insensitively(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _upload(client, _JULY_CSV, "july.csv")

    with session_factory() as session:
        rows = TransactionRepository(session).search(text="swiggy")

    assert [row.description for row in rows] == ["UPI-SWIGGY ORDER"]


def test_search_is_newest_first(client: TestClient, session_factory: sessionmaker[Session]) -> None:
    _upload(client, _JULY_CSV, "july.csv")
    _upload(client, _AUGUST_CSV, "august.csv")

    with session_factory() as session:
        rows = TransactionRepository(session).search(text="swiggy")

    assert [row.transaction_date.isoformat() for row in rows] == ["2026-08-05", "2026-07-01"]


def test_search_treats_percent_and_underscore_literally(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _upload(client, _JULY_CSV, "july.csv")

    with session_factory() as session:
        repo = TransactionRepository(session)
        literal_match = repo.search(text="100% off")
        wildcard_would_match_everything = repo.search(text="_")

    assert [row.description for row in literal_match] == ["100% OFF DISCOUNT_CODE"]
    # "_" must match only a literal underscore, not "any one character".
    assert [row.description for row in wildcard_would_match_everything] == [
        "100% OFF DISCOUNT_CODE"
    ]


def test_search_respects_the_half_open_month_boundary(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _upload(client, _JULY_CSV, "july.csv")
    _upload(client, _AUGUST_CSV, "august.csv")

    with session_factory() as session:
        rows = TransactionRepository(session).search(text="swiggy", month=Month(year=2026, month=7))

    assert [row.transaction_date.isoformat() for row in rows] == ["2026-07-01"]


def test_search_can_combine_month_and_category(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _upload(client, _JULY_CSV, "july.csv")

    with session_factory() as session:
        rows = TransactionRepository(session).search(
            month=Month(year=2026, month=7), category=TransactionCategory.GROCERIES
        )

    assert [row.description for row in rows] == ["UPI-BLINKIT GROCERY"]


def test_search_limit_is_respected(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _upload(client, _JULY_CSV, "july.csv")

    with session_factory() as session:
        rows = TransactionRepository(session).search(limit=2)

    assert len(rows) == 2


def test_search_with_no_filters_returns_everything_newest_first(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    _upload(client, _JULY_CSV, "july.csv")

    with session_factory() as session:
        rows = TransactionRepository(session).search(limit=50)

    assert len(rows) == 4
    assert rows[0].transaction_date.isoformat() == "2026-07-04"
