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

## LangGraph Studio (visual graph debugger)

Runs on the host venv, against the same graph code the backend uses:

```bash
source .venv/bin/activate
langgraph dev                      # from the repo root; needs a free LangSmith login
```

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

## Layout

```
backend/app/          FastAPI app (api → services → repositories layering)
backend/app/graphs/   LangGraph graphs (hello = Phase 0 proof; statement pipeline comes in Phase 1)
backend/app/db/       engine/session + Alembic migrations
frontend/             Vite + React + TS
langgraph.json        points LangGraph Studio at the graphs
```
