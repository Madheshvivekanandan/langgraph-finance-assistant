"""API tests for the dashboard aggregates."""

from fastapi.testclient import TestClient

# Two months, so the trend has something to plot. July: 486 dining out,
# 85000 salary in. August: 1000 groceries out.
_JULY_CSV = (
    b"Date,Description,Amount\n"
    b"01/07/2026,UPI-SWIGGY ORDER,-486.00\n"
    b"02/07/2026,SALARY CREDIT,85000.00\n"
    b"03/07/2026,UPI-BLINKIT,-1000.00\n"
)
_AUGUST_CSV = b"Date,Description,Amount\n05/08/2026,UPI-BIGBASKET,-1000.00\n"


def _upload(client: TestClient, content: bytes, name: str) -> None:
    client.post("/api/v1/statements", files={"file": (name, content, "text/csv")})


def test_monthly_summary_totals_income_expense_and_net(client: TestClient) -> None:
    _upload(client, _JULY_CSV, "july.csv")

    body = client.get("/api/v1/summary/months").json()

    assert body["items"] == [
        {
            "month": "2026-07",
            "income": "85000.00",
            "expense": "1486.00",
            "net": "83514.00",
            "transaction_count": 3,
        }
    ]


def test_monthly_summary_is_newest_first(client: TestClient) -> None:
    _upload(client, _JULY_CSV, "july.csv")
    _upload(client, _AUGUST_CSV, "august.csv")

    months = [item["month"] for item in client.get("/api/v1/summary/months").json()["items"]]

    assert months == ["2026-08", "2026-07"]


def test_category_summary_excludes_income_and_sorts_by_size(client: TestClient) -> None:
    _upload(client, _JULY_CSV, "july.csv")

    body = client.get("/api/v1/summary/categories").json()

    assert [item["category"] for item in body["items"]] == ["GROCERIES", "DINING"]
    assert [item["amount"] for item in body["items"]] == ["1000.00", "486.00"]
    # Salary is income; a "where did money go" breakdown must not include it.
    assert "INCOME" not in [item["category"] for item in body["items"]]
    assert body["total"] == "1486.00"


def test_category_summary_can_be_scoped_to_one_month(client: TestClient) -> None:
    _upload(client, _JULY_CSV, "july.csv")
    _upload(client, _AUGUST_CSV, "august.csv")

    body = client.get("/api/v1/summary/categories", params={"month": "2026-08"}).json()

    assert body["month"] == "2026-08"
    assert [item["category"] for item in body["items"]] == ["GROCERIES"]
    assert body["total"] == "1000.00"


def test_month_boundaries_do_not_leak_between_adjacent_months(client: TestClient) -> None:
    """The half-open range is what stops 1 August counting as July."""
    _upload(client, _JULY_CSV, "july.csv")
    _upload(client, _AUGUST_CSV, "august.csv")

    july = client.get("/api/v1/summary/categories", params={"month": "2026-07"}).json()

    assert july["total"] == "1486.00"


def test_categories_are_empty_before_anything_is_uploaded(client: TestClient) -> None:
    body = client.get("/api/v1/summary/categories").json()

    assert body["items"] == []
    assert body["total"] == "0.00"


def test_invalid_month_returns_problem_json(client: TestClient) -> None:
    response = client.get("/api/v1/summary/categories", params={"month": "2026-13"})

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "INVALID_MONTH"


def test_transactions_can_be_filtered_by_month(client: TestClient) -> None:
    _upload(client, _JULY_CSV, "july.csv")
    _upload(client, _AUGUST_CSV, "august.csv")

    body = client.get("/api/v1/transactions", params={"month": "2026-08"}).json()

    assert [item["transaction_date"] for item in body["items"]] == ["2026-08-05"]


def test_transactions_can_be_filtered_by_category(client: TestClient) -> None:
    _upload(client, _JULY_CSV, "july.csv")

    body = client.get("/api/v1/transactions", params={"category": "DINING"}).json()

    assert [item["description"] for item in body["items"]] == ["UPI-SWIGGY ORDER"]


def test_month_and_category_filters_combine(client: TestClient) -> None:
    _upload(client, _JULY_CSV, "july.csv")
    _upload(client, _AUGUST_CSV, "august.csv")

    body = client.get(
        "/api/v1/transactions", params={"month": "2026-07", "category": "GROCERIES"}
    ).json()

    assert [item["description"] for item in body["items"]] == ["UPI-BLINKIT"]


def test_unknown_category_filter_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/transactions", params={"category": "NONSENSE"})

    assert response.status_code == 422
