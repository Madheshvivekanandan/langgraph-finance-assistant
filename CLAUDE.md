# My Finance

Personal finance app built to learn **LangGraph**. Upload a bank statement CSV → a LangGraph
pipeline parses and categorizes it → a dashboard shows where the money went → (Phase 4) a chat
agent answers questions about it.

Plan and phase status: [docs/PLAN.md](docs/PLAN.md). LangGraph notes: [docs/langgraph-reference.md](docs/langgraph-reference.md).

## Run and verify

```sh
docker compose up -d --build        # postgres → migrate → backend :8000 → frontend :5173 → pgweb :8081
cd backend && ruff format . && ruff check . && mypy app && pytest -q
cd frontend && npm run lint && npx tsc -b --noEmit && npm run build
python scripts/screenshot_ui.py     # layout gate: overflow, clipping, table alignment
```

Postgres is on host port **5433**, not 5432 — 5432 belongs to another project. Containers reach it
as `postgres:5432`.

## Load the standard before writing code

`.claude/skills/` holds the coding standards for this repo. Load the relevant one **before**
writing or reviewing code, not after:

| Touching | Load |
|---|---|
| Any `.py` | `python-best-practices` |
| Any `.tsx` / `.ts` / CSS | `react-best-practices` |
| DDL, migrations, indexes | `sql-schema-design-best-practices` |
| An HTTP endpoint or schema | `api-contract-design-best-practices` |
| Dockerfile, compose, CI | `docker-deployment-best-practices` |
| Commits, branches, PRs | `git-commit-pr-workflow` |
| Any chart or dashboard | `dataviz` |

## Conventions that are not obvious from the code

- **One class per file**, module named after the class. Exceptions: a class's own private helpers,
  a small enum belonging to one class, and exception subclasses grouped in `exceptions.py`.
- **Money is `Decimal`**, stored `numeric(14,2)`, always positive, with `direction` carrying the
  sign. It crosses the wire as a **string**, never a float.
- **Date ranges are half-open** `[start, end)`. Never `BETWEEN` over dates — it double-counts the
  boundary day.
- **Expected failures travel as graph state** and route to `record_failure`; unexpected ones raise.
  A node that raises cannot report through state, which is why `store_transactions` alone carries
  an `error_handler`.
- **Tests own `myfinance_test`.** They create and migrate it themselves and refuse to truncate any
  database whose name does not end in `_test`. Never point them at the development database.
- **Never push, merge, or open a PR** without being asked. Work on a branch; the human merges.

## Staged agent loop

For substantial changes — a new feature, a multi-file refactor, anything where a wrong approach is
expensive — run the **agent-loop** skill at `.claude/skills/agent-loop/SKILL.md` instead of editing
directly. It triages the task, then runs analyze → plan → implement → verify → debug with
file-based handoff and an independent verification stage that cannot edit code.

Invoke it explicitly (`/agent-loop <task>`, or "run the agent loop on this"). Do not auto-select it
for small edits — it is deliberately heavier than a direct change, and its own triage exists to keep
ceremony proportional.

Its stages are still bound by everything above: the standards table, the conventions, and the
verification commands. Run artifacts land in `.agent-loop/` (gitignored) as the audit log of what
was decided and why.
