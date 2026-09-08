# My Finance — Project Plan

## Why this project exists

Primary goal: **learn to build graphs and agents with LangGraph**, by building something personally useful. The app is the vehicle; every phase is sized so the LangGraph concept it teaches stays visible. Simplicity beats completeness — single user, no auth, CSV before PDF.

## The idea, elaborated

Upload a monthly bank statement → a LangGraph pipeline parses it into transactions and categorizes them → a dashboard visualizes spending by month and category → a chat agent answers questions like "what happened to my money in July?" using tools that query the database.

Two graphs, deliberately different in shape, so both major LangGraph styles get learned:

1. **Statement pipeline** — a deterministic `StateGraph` workflow (parse → normalize → categorize → store). Teaches nodes, state, reducers, conditional edges, retries.
2. **Finance chat agent** — a `create_agent` tool-calling agent with DB query tools and Postgres-checkpointed memory. Teaches agents, tools, checkpointers/threads, streaming.

## Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2 + Alembic, LangGraph 1.2.x, `langchain-anthropic`
- **Database:** Postgres (docker-compose) — app tables + LangGraph checkpointer tables
- **Frontend:** Vite + React 18 + TypeScript + MUI, Recharts for charts (skip Refine for now — fewer moving parts while learning)
- **Dev tooling:** LangGraph Studio via `langgraph dev` (graph visualization + step-through debugging), ruff/black/mypy, pytest

## Repo layout (target)

```
My_Finance/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app factory
│   │   ├── api/v1/routes/       # upload, transactions, chat endpoints
│   │   ├── graphs/
│   │   │   ├── statement/       # state.py, nodes/, graph.py  (pipeline)
│   │   │   └── chat/            # tools/, agent.py            (chat agent)
│   │   ├── services/  repositories/  models/  schemas/  core/  db/
│   │   └── ...                  # per python-best-practices skill (one class per file)
│   ├── tests/
│   └── pyproject.toml
├── frontend/                    # Vite + React + TS + MUI
├── docs/                        # this plan, langgraph-reference.md
├── langgraph.json               # points Studio at both graphs
├── docker-compose.yml           # postgres
└── .env.example
```

## Data model (minimal)

- `statements` — id, filename, period_month, uploaded_at, status
- `transactions` — id, statement_id FK, date, description, amount (Decimal), direction, category, categorized_by (rule|llm|user), confidence
- `categories` — seeded lookup (Groceries, Rent, Transport, Dining, Salary, …)
- Chat memory lives in LangGraph's own checkpointer tables — nothing to design.

## Phases

Each phase ends with something runnable and one LangGraph concept understood.

### Phase 0 — Skeleton + first graph visible in Studio  ✅ **done**  *(learn: StateGraph basics, Studio)*
Scaffold backend/frontend, docker-compose Postgres, Alembic baseline. Build a trivial 2-node hello graph, wire `langgraph.json`, run `langgraph dev`, see it and step through it in Studio. **Done when:** graph renders and runs in Studio; FastAPI `/health` and React hello page work.

### Phase 1 — CSV statement upload → transactions in DB  ✅ **done**  *(learn: state schemas, nodes, conditional edges, error handling)*
Upload endpoint accepts a bank CSV. Statement pipeline v1: `parse_csv → normalize → store` with a conditional edge to an error path for malformed files, `retry_policy` on flaky nodes. Plain transactions table view in React. **Done when:** uploading a real statement shows its transactions in the UI, and the run is inspectable step-by-step in Studio.

### Phase 2 — Categorization  *(learn: LLM nodes, structured output)*
Add `categorize` node: rules first (regex/merchant map — free and instant), LLM fallback with structured output for the rest, batched to keep cost low. Store category + confidence + who categorized. Manual category override in the UI (feeds the rules map). **Done when:** an uploaded statement comes back fully categorized and corrections stick.

### Phase 3 — Dashboard  *(learn: nothing new in LangGraph — pure product payoff)*
Monthly summary (income/expense/net), category breakdown donut, month-over-month trend line, filterable transaction table. Follow the dataviz skill for the charts. **Done when:** you can see where a month's money went at a glance.

### Phase 4 — Chat agent  *(learn: create_agent, tools, checkpointer memory, streaming)*
`create_agent` with 2–3 safe tools (`get_monthly_summary`, `search_transactions`, `spending_by_category`) — tools call repositories, never raw SQL from the LLM. `AsyncPostgresSaver` + `thread_id` for conversation memory; SSE streaming to a React chat panel. **Done when:** "how much did I spend on dining in July?" gets a correct, streamed answer with follow-up memory.

### Phase 5 (optional, later) — Stretch goals
PDF statement parsing; `interrupt()` human-in-the-loop review of low-confidence categorizations (the classic HITL lesson); embed a live mermaid/React Flow graph view in the frontend; multi-month insights ("recurring subscriptions", anomaly flags).

## Simplicity guardrails

- Single user, no auth until it hurts.
- CSV only until Phase 5.
- No LangGraph Platform / Agent Server in production — graphs embed in FastAPI; `langgraph dev` is dev-only.
- Two graphs total. Resist adding more agents; deepen these instead.
