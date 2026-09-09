"""The feature test: a real agent + real PostgresSaver against myfinance_test.

Dining-in-July drives a real tool call through TransactionSearchService and
SummaryService to real seeded rows; a second turn on the same thread_id proves
the checkpointer is carrying conversation memory.
"""

import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy.orm import Session, sessionmaker

from app.graphs.chat.graph import build_chat_agent
from tests.fakes.fake_chat_model import FakeChatModel

_JULY_CSV = (
    b"Date,Description,Amount\n"
    b"01/07/2026,UPI-SWIGGY ORDER,-486.00\n"
    b"02/07/2026,SALARY CREDIT,85000.00\n"
    b"10/07/2026,UPI-ZOMATO ORDER,-320.00\n"
)


def _upload(client: TestClient, content: bytes, name: str) -> None:
    response = client.post("/api/v1/statements", files={"file": (name, content, "text/csv")})
    assert response.status_code < 400


def test_a_dining_question_drives_a_real_tool_call_to_an_exact_total(
    client: TestClient,
    session_factory: sessionmaker[Session],
    chat_checkpointer: PostgresSaver,
) -> None:
    _upload(client, _JULY_CSV, "july.csv")

    fake = FakeChatModel(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_spending_by_category",
                        "args": {"month": "2026-07"},
                        "id": "call_1",
                    }
                ],
            ),
            AIMessage(content="You spent 806.00 on dining in July."),
        ]
    )
    agent = build_chat_agent(session_factory, fake, checkpointer=chat_checkpointer)
    thread_id = str(uuid.uuid4())

    result = agent.invoke(
        {"messages": [HumanMessage(content="how much did I spend on dining in July?")]},
        config={"configurable": {"thread_id": thread_id}},
    )

    tool_message = result["messages"][2]
    assert tool_message.type == "tool"
    # DINING = 486.00 (SWIGGY) + 320.00 (ZOMATO) = 806.00, exact.
    assert '"category": "DINING"' in tool_message.content
    assert '"amount": "806.00"' in tool_message.content
    assert Decimal("806.00") == Decimal("486.00") + Decimal("320.00")
    assert result["messages"][-1].content == "You spent 806.00 on dining in July."


def test_a_second_turn_on_the_same_thread_remembers_the_first(
    session_factory: sessionmaker[Session],
    chat_checkpointer: PostgresSaver,
) -> None:
    fake = FakeChatModel(
        [
            AIMessage(content="Hi, ask me about your spending."),
            AIMessage(content="You already asked about dining."),
        ]
    )
    agent = build_chat_agent(session_factory, fake, checkpointer=chat_checkpointer)
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    agent.invoke({"messages": [HumanMessage(content="hello")]}, config=config)
    agent.invoke({"messages": [HumanMessage(content="what did I just ask?")]}, config=config)

    # Turn 2's model call must have seen turn 1's human message in its context.
    second_call_messages = fake.calls[1]
    assert any(
        isinstance(message, HumanMessage) and message.content == "hello"
        for message in second_call_messages
    )


def test_a_different_thread_does_not_see_another_threads_history(
    session_factory: sessionmaker[Session],
    chat_checkpointer: PostgresSaver,
) -> None:
    fake = FakeChatModel(
        [
            AIMessage(content="Hi, ask me about your spending."),
            AIMessage(content="I don't have context on that."),
        ]
    )
    agent = build_chat_agent(session_factory, fake, checkpointer=chat_checkpointer)
    first_thread = str(uuid.uuid4())
    second_thread = str(uuid.uuid4())

    agent.invoke(
        {"messages": [HumanMessage(content="hello")]},
        config={"configurable": {"thread_id": first_thread}},
    )
    agent.invoke(
        {"messages": [HumanMessage(content="what did I just ask?")]},
        config={"configurable": {"thread_id": second_thread}},
    )

    second_call_messages = fake.calls[1]
    assert not any(
        isinstance(message, HumanMessage) and message.content == "hello"
        for message in second_call_messages
    )
