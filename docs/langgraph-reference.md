# LangGraph Reference Notes (researched 2026-09-08)

Condensed findings for this project. Sources: docs.langchain.com, PyPI, LangChain blog.

## Versions & packages

- LangGraph **1.2.x** is current stable (1.0 GA'd Oct 2025). Python **3.10+**. No breaking changes promised until 2.0 — pin `langgraph>=1.2,<2`.
- Install for this project: `langgraph`, `langchain` (1.x), `langgraph-checkpoint-postgres`, `langchain-anthropic`, `langgraph-cli[inmem]` (dev only).
- **Deprecated:** `langgraph.prebuilt.create_react_agent`. Use **`langchain.agents.create_agent`** instead (returns a compiled graph, supports middleware for HITL/guardrails/summarization).

## Core idiom

```python
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain.agents import create_agent

class State(TypedDict):
    messages: Annotated[list, add_messages]   # reducer controls merge

builder = StateGraph(State)
builder.add_node("triage", triage)            # plain function node
builder.add_node("research", create_agent(model="anthropic:claude-sonnet-4-5", tools=[...]))
builder.add_edge(START, "triage")
builder.add_conditional_edges("triage", route, {"research": "research", "done": END})
graph = builder.compile(checkpointer=checkpointer)
```

- State schema: **TypedDict by default**; Pydantic only if runtime validation is needed (`create_agent` doesn't support Pydantic state).
- Three APIs: `create_agent` (standard tool-calling agent), `StateGraph` (explicit workflows/branching — our main tool), Functional API `@entrypoint`/`@task` (wrap procedural code). They compose; a compiled agent can be a node.

## Persistence / checkpointers

- `InMemorySaver` dev/tests only. Production: **`AsyncPostgresSaver`** (`langgraph-checkpoint-postgres`, psycopg 3). Run `await cp.setup()` once to create tables.
- Every checkpointed invocation needs `config={"configurable": {"thread_id": "<uuid>"}}`. Checkpointer enables chat memory, HITL resume, and time-travel.

## Serving pattern (ours)

- **Embed in FastAPI**: compile the graph with the Postgres checkpointer in the FastAPI lifespan; routes call `graph.astream(...)`. FastAPI owns auth/validation/SSE; graph owns agent logic.
- Keep the compiled graph importable by BOTH FastAPI and **`langgraph.json`** so `langgraph dev` (LangGraph Studio) works against the same code:

```json
{
  "dependencies": ["./backend"],
  "graphs": { "statement": "./backend/app/graphs/statement/graph.py:graph" },
  "env": ".env"
}
```

## Production features to use

- **Streaming:** `stream_mode` = `values` | `updates` | `messages` | `custom`; new typed streaming `version="v2"` recommended.
- **Human-in-the-loop:** `interrupt()` inside a node pauses (state checkpointed); resume with `graph.invoke(Command(resume=value), config)`. Resume values must be JSON-serializable.
- **Retries/timeouts:** per-node `retry_policy=RetryPolicy(...)` on `add_node`; LangGraph ≥1.2 adds per-node `TimeoutPolicy` and node error handlers.
- **Subgraphs:** pass a compiled graph to `add_node` (shared keys) or wrap in a translating node (different schemas).

## Visualization

1. **Built-in:** `graph.get_graph(xray=1).draw_mermaid()` → Mermaid text; `draw_mermaid_png()` → image (uses Mermaid.Ink API by default; `MermaidDrawMethod.PYPPETEER` for offline). Static structure only.
2. **LangGraph Studio (main dev tool):** `langgraph dev` → free browser IDE at smith.langchain.com/studio talking to the LOCAL server. Interactive graph, live step-through, state inspection at each node, time-travel/fork-from-step, hot reload. Needs a free LangSmith login; agent runs locally (`LANGSMITH_TRACING=false` keeps data local). Safari needs `--tunnel`.
3. **In our React frontend (later, product feature only):** FastAPI endpoint returning `draw_mermaid()` + `mermaid` npm package; or graph-JSON + React Flow, animated via the official `useStream()` hook from `@langchain/langgraph-sdk/react`.
4. **Tracing:** LangSmith free tier = 5k traces/mo, 14-day retention. Self-host alternative: Langfuse (has an Agent Graphs view that steps through runs on the diagram).

## Docs moved

Official docs live at `docs.langchain.com/oss/python/langgraph/...` (not the old langchain-ai.github.io). API reference: reference.langchain.com. LangGraph Platform is being rebranded "LangSmith Deployments" (we don't need it — we embed in FastAPI).
