# My Finance

Upload monthly bank statements, get them categorized, visualize spending, and chat with an
agent about your finances. Built to learn **LangGraph** — plan in [docs/PLAN.md](docs/PLAN.md),
LangGraph notes in [docs/langgraph-reference.md](docs/langgraph-reference.md).

**Stack:** FastAPI + LangGraph + SQLAlchemy/Alembic + Postgres · Vite + React + TypeScript

## Setup (once)

```bash
cp .env.example .env          # then fill in OPENAI_API_KEY
python3 -m venv .venv
source .venv/bin/activate
pip install -e './backend[dev]'
cd frontend && npm install
```

## Run (everything in Docker)

```bash
docker compose up -d --build
```

That brings up, in order: **postgres** (host port 5433 — 5432 is taken by another project) →
**migrate** (one-shot `alembic upgrade head`, then exits) → **backend** on
http://localhost:8000 (uvicorn --reload against the bind-mounted source) → **frontend** on
http://localhost:5173 (Vite dev server with HMR, proxying `/api` to the backend container).

Code changes on the host hot-reload inside the containers. After changing backend
dependencies (`pyproject.toml`) or frontend deps (`package.json`), rebuild:
`docker compose up -d --build`.

```bash
docker compose logs -f backend     # tail the API logs
docker compose down                # stop everything (data survives in the pgdata volume)
```

## Try it

A sample statement is included:

```bash
curl -X POST http://localhost:5173/api/v1/statements \
  -F "file=@sample-data/july-2026-statement.csv"
```

Or open http://localhost:5173 and upload it through the UI.

## API (v1)

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/statements` | Upload a statement CSV; runs the ingestion graph. 201 with the outcome, 409 if already uploaded |
| `GET /api/v1/statements` | Recent statements with their status |
| `GET /api/v1/transactions` | Transactions, newest first, keyset-paginated via `page_size` + `page_token`; filter with `month` (YYYY-MM) and `category` |
| `PUT /api/v1/transactions/{id}/category` | Override a category; records the source as USER |
| `GET /api/v1/categories` | The category vocabulary the UI offers |
| `GET /api/v1/summary/months` | Income, expense, and net per month |
| `GET /api/v1/summary/categories` | Spending by category, optionally for one month |
| `GET /api/v1/health` | Liveness |

Errors are `application/problem+json` (RFC 9457) with a stable `code` field.
Interactive docs at http://localhost:8000/docs.

### Supported statement CSVs

Column names are matched case-insensitively against common aliases, in either layout:

- **Signed amount:** `Date`, `Description`, `Amount` (negative = money out)
- **Debit/credit pair:** `Transaction Date`, `Narration`, `Withdrawal Amount`, `Deposit Amount`

Dates are read **day-first** (`03/04/2026` is 3 April), matching Indian bank exports.
Unreadable rows (opening balances, footers) are skipped; a file where nothing is
readable is stored as `FAILED` with the reason.

## Dashboard

The home page opens on a dashboard: income / expense / net tiles, a month-by-month
trend, and a bar chart of where the money went. Pick a period from the filter row,
or click a category bar to filter the transaction table below it.

Two conventions worth knowing, both deliberate:

- **`expense` counts every debit**, transfers and investments included — money that
  left the account left the account. The category breakdown is where that
  distinction becomes visible.
- **The category breakdown is debits only.** A picture of where money went should
  not have salary mixed into it.

## Categorization

Every ingested transaction is categorized in two stages, cheapest first:

1. **Keyword rules** (`backend/app/graphs/statement/category_rules.py`) — free,
   instant, deterministic. Handles most Indian bank descriptions (SWIGGY, BLINKIT,
   TNEB, ATM, SALARY, …).
2. **OpenAI fallback** — only the rows no rule matched, batched into one call, with
   the category set enforced by the response schema rather than by the prompt.

If the rules categorize everything, **the model is never called**. If
`OPENAI_API_KEY` is missing, ingestion still succeeds and those rows stay
`UNCATEGORIZED` — categorization enriches a statement, it does not define one.

Correct anything in the UI: the stored source becomes `USER`, and any model
confidence is cleared.

## LangGraph Studio (visual graph debugger)

Runs on the host venv, against the same graph code the backend uses:

```bash
source .venv/bin/activate
langgraph dev                      # from the repo root; needs a free LangSmith login
```

Pick the **statement** graph and give it just a CSV — it creates its own statement
record, so nothing needs to exist beforehand:

```json
{ "raw_csv": "Date,Description,Amount\n01/07/2026,SWIGGY,-450.00\n" }
```

Re-running identical CSV text raises `DuplicateStatementError`: the unique file
hash is what stops a statement being counted twice. Change a value to run again.

## Run without Docker (host venv, optional)

```bash
docker compose up -d postgres
cd backend && alembic upgrade head
uvicorn app.main:app --app-dir backend --reload --port 8000   # terminal 1
cd frontend && npm run dev                                    # terminal 2
```

## Quality gates (backend)

```bash
cd backend
ruff format . && ruff check . && mypy app && pytest -q
```

Tests run against a separate **`myfinance_test`** database, created and migrated
automatically on first run. They never touch your development data — the
integration fixtures refuse to truncate any database whose name does not end in
`_test`.

## Checking the UI

A palette validator checks colour, not geometry, so the layout gets rendered and
inspected instead of eyeballed:

```bash
playwright install chromium     # once
python scripts/screenshot_ui.py # app must be running
```

It screenshots mobile, tablet, and desktop (light and dark) into `.screenshots/`,
and exits non-zero if the page scrolls horizontally or any label is clipped.

## Layout

```
backend/app/          FastAPI app (api → services → repositories layering)
backend/app/graphs/   LangGraph graphs (statement = the ingestion pipeline; hello = Phase 0 proof)
backend/app/db/       engine/session + Alembic migrations
frontend/             Vite + React + TS
langgraph.json        points LangGraph Studio at the graphs
```
