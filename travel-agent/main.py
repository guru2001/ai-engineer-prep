from typing import Literal, Annotated

import chainlit as cl
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import MessagesState

model = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

TRIP_PLANNER_SYSTEM_PROMPT = (
    "You are TravelBuddy, an upbeat but practical trip planning assistant. "
    "Users should be able to ask for suggestions for a trip based on their dates, "
    "budget, destination, interests, and travel group (e.g. solo, couple, family, friends). "
    "Always gather or infer these details, then suggest a concrete itinerary, activities, "
    "transportation, and dining tailored to them."
)


def passthrough_node(state: MessagesState) -> MessagesState:
    # This node simply returns the accumulated message history.
    return state


builder = StateGraph(MessagesState)
builder.add_node("history", passthrough_node)
builder.add_edge(START, "history")
builder.add_edge("history", END)

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)


@cl.on_message
async def on_message(user_msg: cl.Message):
    thread_id = cl.context.session.id
    config = RunnableConfig(configurable={"thread_id": thread_id})

    # First, update LangGraph state with the new user message and get full history,
    # using graph.stream so this remains LangGraph-driven and extensible.
    last_state: MessagesState | None = None
    for state in graph.stream(
        {"messages": [HumanMessage(content=user_msg.content)]},
        config=config,
        stream_mode="values",
    ):
        last_state = state

    history_messages: list[BaseMessage] = (
        last_state["messages"] if last_state is not None else []
    )

    # Build messages for the LLM: system prompt + full history.
    messages: list[BaseMessage] = [
        SystemMessage(TRIP_PLANNER_SYSTEM_PROMPT),
        *history_messages,
    ]

    # Thinking step for the UI.
    async with cl.Step(
        name="Trip Planning", parent_id=user_msg.id
    ) as step:
        step.output = "Mapping out itinerary ideas and next steps."

    # Stream answer tokens.
    final_answer = cl.Message(content="")
    full_content = ""
    async for chunk in model.astream(messages):
        delta = chunk.content or ""
        full_content += delta
        await final_answer.stream_token(delta)

    await final_answer.send()

    # Append assistant reply into LangGraph history as an AIMessage.
    graph.invoke(
        {"messages": [AIMessage(content=full_content)]},
        config=config,
    )