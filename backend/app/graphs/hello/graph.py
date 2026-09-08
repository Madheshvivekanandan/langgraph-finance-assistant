"""Hello graph: the Phase 0 two-node StateGraph.

Exists to prove the LangGraph toolchain end to end (compile, invoke, and render
in LangGraph Studio via langgraph.json). Replaced by real graphs in later phases.
"""

from langgraph.graph import END, START, StateGraph

from app.graphs.hello.nodes import add_welcome, compose_greeting
from app.graphs.hello.state import HelloState

builder = StateGraph(HelloState)
builder.add_node("compose_greeting", compose_greeting)
builder.add_node("add_welcome", add_welcome)
builder.add_edge(START, "compose_greeting")
builder.add_edge("compose_greeting", "add_welcome")
builder.add_edge("add_welcome", END)

graph = builder.compile()
