"""API tests for statement upload and transaction listing."""

from fastapi.testclient import TestClient

_GOOD_CSV = (
    b"Date,Description,Amount\n"
    b"01/07/2026,SWIGGY ORDER,-450.00\n"
    b"02/07/2026,SALARY JULY,85000.00\n"
    b"15/07/2026,ELECTRICITY BILL,-2340.50\n"
)


def _upload(client: TestClient, content: bytes, filename: str = "july.csv"):  # noqa: ANN202
    return client.post("/api/v1/statements", files={"file": (filename, content, "text/csv")})


def test_upload_returns_201_with_location_and_completed_status(client: TestClient) -> None:
    response = _upload(client, _GOOD_CSV)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["transaction_count"] == 3
    assert response.headers["Location"] == f"/api/v1/statements/{body['id']}"


def test_uploaded_transactions_are_listed_newest_first(client: TestClient) -> None:
    _upload(client, _GOOD_CSV)

    body = client.get("/api/v1/transactions").json()

    assert [item["transaction_date"] for item in body["items"]] == [
        "2026-07-15",
        "2026-07-02",
        "2026-07-01",
    ]
    # Money crosses the wire as a string, never a float.
    assert body["items"][0]["amount"] == "2340.50"
    # No next token on the last page - it is omitted, not null.
    assert "next" not in body


def test_transaction_pages_follow_the_cursor_without_gaps_or_repeats(
    client: TestClient,
) -> None:
    _upload(client, _GOOD_CSV)

    first = client.get("/api/v1/transactions", params={"page_size": 2}).json()
    assert len(first["items"]) == 2
    assert "next" in first

    second = client.get(
        "/api/v1/transactions", params={"page_size": 2, "page_token": first["next"]}
    ).json()

    seen = [item["id"] for item in first["items"] + second["items"]]
    assert len(seen) == len(set(seen)) == 3


def test_oversized_page_size_is_clamped_rather_than_rejected(client: TestClient) -> None:
    _upload(client, _GOOD_CSV)

    response = client.get("/api/v1/transactions", params={"page_size": 10_000})

    assert response.status_code == 200


def test_invalid_page_token_returns_problem_json(client: TestClient) -> None:
    response = client.get("/api/v1/transactions", params={"page_token": "nonsense!"})

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "INVALID_PAGE_TOKEN"


def test_reuploading_the_same_file_is_rejected_as_a_duplicate(client: TestClient) -> None:
    assert _upload(client, _GOOD_CSV).status_code == 201

    response = _upload(client, _GOOD_CSV, filename="july-again.csv")

    assert response.status_code == 409
    assert response.json()["code"] == "STATEMENT_ALREADY_UPLOADED"


def test_unreadable_file_is_recorded_as_failed_not_crashed(client: TestClient) -> None:
    response = _upload(client, b"Foo,Bar\n1,2\n", filename="junk.csv")

    # The upload itself succeeds; the statement carries the failure.
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "FAILED"
    assert "date column" in body["error_message"]
    assert client.get("/api/v1/transactions").json()["items"] == []


def test_empty_file_is_rejected_with_problem_json(client: TestClient) -> None:
    response = _upload(client, b"", filename="empty.csv")

    assert response.status_code == 422
    assert response.json()["code"] == "STATEMENT_UNREADABLE"


def test_uploaded_statements_are_listed(client: TestClient) -> None:
    _upload(client, _GOOD_CSV)

    body = client.get("/api/v1/statements").json()

    assert len(body["items"]) == 1
    assert body["items"][0]["filename"] == "july.csv"
