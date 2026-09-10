# My Finance — Project Plan

## Why this project exists

Primary goal: **learn to build graphs and agents with LangGraph**, by building something personally useful. The app is the vehicle; every phase is sized so the LangGraph concept it teaches stays visible. Simplicity beats completeness — single user, no auth, CSV before PDF.

## The idea, elaborated

Upload a monthly bank statement → a LangGraph pipeline parses it into transactions and categorizes them → a dashboard visualizes spending by month and category → a chat agent answers questions like "what happened to my money in July?" using tools that query the database.

Two graphs, deliberately different in shape, so both major LangGraph styles get learned:

1. **Statement pipeline** — a deterministic `StateGraph` workflow (parse → normalize → categorize → store). Teaches nodes, state, reducers, conditional edges, retries.
2. **Finance chat agent** — a `create_agent` tool-calling agent with DB query tools and Postgres-checkpointed memory. Teaches agents, tools, checkpointers/threads, streaming.

## Stack

- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2 + Alembic, LangGraph 1.2.x, `langchain-openai`
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
- categories — a `TransactionCategory` enum in code, enforced by a CHECK constraint (no lookup table: the set is small and stable, and one definition keeps the rules, the model prompt, and the database from drifting apart)
- Chat memory lives in LangGraph's own checkpointer tables — nothing to design.

## Phases

Each phase ends with something runnable and one LangGraph concept understood.

### Phase 0 — Skeleton + first graph visible in Studio  ✅ **done**  *(learn: StateGraph basics, Studio)*
Scaffold backend/frontend, docker-compose Postgres, Alembic baseline. Build a trivial 2-node hello graph, wire `langgraph.json`, run `langgraph dev`, see it and step through it in Studio. **Done when:** graph renders and runs in Studio; FastAPI `/health` and React hello page work.

### Phase 1 — CSV statement upload → transactions in DB  ✅ **done**  *(learn: state schemas, nodes, conditional edges, error handling)*
Upload endpoint accepts a bank CSV. Statement pipeline v1: `parse_csv → normalize → store` with a conditional edge to an error path for malformed files, `retry_policy` on flaky nodes. Plain transactions table view in React. **Done when:** uploading a real statement shows its transactions in the UI, and the run is inspectable step-by-step in Studio.

### Phase 2 — Categorization  ✅ **done**  *(learn: LLM nodes, structured output)*
Add `categorize` node: rules first (regex/merchant map — free and instant), LLM fallback with structured output for the rest, batched to keep cost low. Store category + confidence + who categorized. Manual category override in the UI. (Rules live in code, not a table; having a correction auto-write a new rule needs fuzzy merchant extraction, deferred to Phase 5.) **Done when:** an uploaded statement comes back fully categorized and corrections stick.

### Phase 3 — Dashboard  ✅ **done**  *(learn: nothing new in LangGraph — pure product payoff)*
Monthly summary (income/expense/net) as KPI tiles, category breakdown as a **bar chart** (not a donut — the dataviz skill is clear that bar length beats arc angle for magnitude comparison), month-over-month trend line, filterable transaction table. **Done when:** you can see where a month's money went at a glance.

### Phase 4 — Chat agent  ✅ **done**  *(learn: create_agent, tools, checkpointer memory, streaming)*
`create_agent` with 3 safe tools (`get_monthly_summary`, `get_spending_by_category`, `search_transactions`) — tools call services/repositories, never raw SQL from the LLM. `PostgresSaver` + `thread_id` for conversation memory; SSE streaming to a React chat panel. **Done when:** "how much did I spend on dining in July?" gets a correct, streamed answer with follow-up memory.

**Deviation from this plan:** uses the **sync** `langgraph.checkpoint.postgres.PostgresSaver`, not `AsyncPostgresSaver`. Every repository, service, and route in this codebase is sync SQLAlchemy; FastAPI already runs `def` routes (and iterates a sync `StreamingResponse` generator) in its threadpool, so a fully sync graph/tools/route never blocks the event loop and avoids introducing a second, half-finished async stack for one feature. Same tables, same semantics — see `.agent-loop/runs/2026-09-09-phase-4-chat-agent/plan.md` (D1) for the full rationale.

### Phase 5 (optional, later) — Stretch goals

`interrupt()` human-in-the-loop review of low-confidence categorizations (the classic HITL lesson)  ✅ **done**  *(learn: `interrupt()`/`Command(resume=...)`, resuming a suspended run from a real checkpoint)*
A model categorization below a confidence threshold (`LowConfidencePolicy`, default 0.75, gated on `categorized_by is LLM` so a no-key run never pauses) now stops the statement pipeline before `store_transactions`: `mark_awaiting_review` sets the status, `review_low_confidence` calls `interrupt()` with the pending rows and applies whatever decisions come back on resume. The upload endpoint stays synchronous 201; a statement can come back `AWAITING_REVIEW` with zero transactions until `GET`/`POST /api/v1/statements/{id}/review` resolves it. **Done when:** an upload with an unsure categorization leaves the statement awaiting review, the pending rows are visible and correctable in the UI, and approving resumes the same run (same `thread_id`) rather than re-ingesting. See `.agent-loop/runs/2026-09-09-hitl-review/plan.md` for the full rationale, including why a statement nobody reviews simply stays `AWAITING_REVIEW` forever (D8) rather than expiring.

**Follow-up, out of scope for this run:** a discard/abandon endpoint for a statement stuck `AWAITING_REVIEW` that nobody wants to finish reviewing — today the only ways out are "review it" or delete the row directly, and `file_hash` being `UNIQUE` means re-uploading the same file will not start a fresh run.

Still open: PDF statement parsing; embed a live mermaid/React Flow graph view in the frontend; multi-month insights ("recurring subscriptions", anomaly flags).

## Simplicity guardrails

- Single user, no auth until it hurts.
- CSV only until Phase 5.
- No LangGraph Platform / Agent Server in production — graphs embed in FastAPI; `langgraph dev` is dev-only.
- Two graphs total. Resist adding more agents; deepen these instead.
