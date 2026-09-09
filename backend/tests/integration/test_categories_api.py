"""API tests for the category vocabulary and manual overrides."""

from fastapi.testclient import TestClient

_GOOD_CSV = b"Date,Description,Amount\n01/07/2026,UPI-SWIGGY ORDER,-486.00\n"


def _upload(client: TestClient) -> None:
    client.post("/api/v1/statements", files={"file": ("july.csv", _GOOD_CSV, "text/csv")})


def _first_transaction(client: TestClient) -> dict[str, object]:
    return client.get("/api/v1/transactions").json()["items"][0]


def test_categories_endpoint_lists_assignable_categories(client: TestClient) -> None:
    body = client.get("/api/v1/categories").json()

    codes = [item["code"] for item in body["items"]]
    assert "GROCERIES" in codes
    assert {"code": "DINING", "label": "Dining"} in body["items"]
    # UNCATEGORIZED is a state, not something a person picks from a menu.
    assert "UNCATEGORIZED" not in codes


def test_uploaded_transaction_is_categorized_by_rules(client: TestClient) -> None:
    _upload(client)

    transaction = _first_transaction(client)

    assert transaction["category"] == "DINING"
    assert transaction["categorized_by"] == "RULE"
    # A rule records no confidence, and absent fields are omitted, not null.
    assert "confidence" not in transaction


def test_a_person_can_override_the_category(client: TestClient) -> None:
    _upload(client)
    transaction_id = _first_transaction(client)["id"]

    response = client.put(
        f"/api/v1/transactions/{transaction_id}/category", json={"category": "GROCERIES"}
    )

    assert response.status_code == 200
    assert response.json()["category"] == "GROCERIES"
    assert response.json()["categorized_by"] == "USER"


def test_the_override_sticks_on_a_later_read(client: TestClient) -> None:
    _upload(client)
    transaction_id = _first_transaction(client)["id"]

    client.put(f"/api/v1/transactions/{transaction_id}/category", json={"category": "GROCERIES"})

    assert _first_transaction(client)["category"] == "GROCERIES"


def test_override_is_idempotent(client: TestClient) -> None:
    _upload(client)
    transaction_id = _first_transaction(client)["id"]
    url = f"/api/v1/transactions/{transaction_id}/category"

    first = client.put(url, json={"category": "GROCERIES"}).json()
    second = client.put(url, json={"category": "GROCERIES"}).json()

    assert first == second


def test_unknown_category_is_rejected(client: TestClient) -> None:
    _upload(client)
    transaction_id = _first_transaction(client)["id"]

    response = client.put(
        f"/api/v1/transactions/{transaction_id}/category", json={"category": "NOT_A_CATEGORY"}
    )

    assert response.status_code == 422


def test_unknown_transaction_returns_problem_json(client: TestClient) -> None:
    response = client.put("/api/v1/transactions/999999/category", json={"category": "GROCERIES"})

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "TRANSACTION_NOT_FOUND"
