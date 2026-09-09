"""The chat agent: a `create_agent` tool-calling loop over read-only finance tools.

No hand-built StateGraph here - `create_agent` returns a compiled graph directly.
The tools call existing services; the LLM never sees or emits SQL.
"""

from typing import Any

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.orm import Session, sessionmaker

from app.clients.chat_model_factory import build_chat_model
from app.db.session import get_session_factory
from app.graphs.chat.system_prompt import build_system_prompt
from app.graphs.chat.tools.monthly_summary_tool import build_monthly_summary_tool
from app.graphs.chat.tools.search_transactions_tool import build_search_transactions_tool
from app.graphs.chat.tools.spending_by_category_tool import build_spending_by_category_tool
from app.services.summary_service import SummaryService
from app.services.transaction_search_service import TransactionSearchService


def build_chat_agent(
    session_factory: sessionmaker[Session],
    model: BaseChatModel | None,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> CompiledStateGraph[Any, Any, Any, Any] | None:
    """Wire up the chat agent, or return None when no model is available.

    Args:
        session_factory: Injected so tests can point the tools at a throwaway
            database.
        model: None disables the whole feature - `ChatService.is_available()`
            reflects that, and the route 503s rather than starting a broken
            stream.
        checkpointer: None compiles an agent with no conversation memory. The
            module-level `graph` below is compiled this way, matching how
            `graphs/statement/graph.py` exports itself for `langgraph.json` -
            LangGraph Studio supplies its own persistence. FastAPI's lifespan
            compiles a second, checkpointed instance for the live API.
    """
    if model is None:
        return None

    summary_service = SummaryService(session_factory)
    search_service = TransactionSearchService(session_factory)
    tools = [
        build_monthly_summary_tool(summary_service),
        build_spending_by_category_tool(summary_service),
        build_search_transactions_tool(search_service),
    ]
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=build_system_prompt(),
        checkpointer=checkpointer,
    )


# Module-level instance so langgraph.json (and therefore LangGraph Studio) points
# at exactly the graph the API runs. No checkpointer: Studio supplies its own.
# With no OPENAI_API_KEY configured this is None, and the "chat" entry in
# langgraph.json cannot load - Studio-only, and an honest signal.
graph = build_chat_agent(get_session_factory(), build_chat_model())
