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

builder = StateGraph(MessagesState)


def assistant_node(state: MessagesState) -> MessagesState:
    """LangGraph node that calls the LLM and appends its reply to the message history."""
    history_messages: list[BaseMessage] = state.get("messages", [])

    # Build messages for the LLM: system prompt + full history.
    messages: list[BaseMessage] = [
        SystemMessage(TRIP_PLANNER_SYSTEM_PROMPT),
        *history_messages,
    ]

    ai_reply: AIMessage = model.invoke(messages)  # type: ignore[assignment]

    # Thanks to the `add_messages` reducer on MessagesState, returning
    # a dict with "messages": [ai_reply] will append this to the history.
    return {"messages": [ai_reply]}


builder.add_node("assistant", assistant_node)
builder.add_edge(START, "assistant")
builder.add_edge("assistant", END)

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)


@cl.on_message
async def on_message(user_msg: cl.Message):
    thread_id = cl.context.session.id
    config = RunnableConfig(configurable={"thread_id": thread_id})

    # Thinking step for the UI.
    async with cl.Step(
        name="Trip Planning", parent_id=user_msg.id
    ) as step:
        step.output = "Mapping out itinerary ideas and next steps."

    # Use LangGraph's event stream so we can stream model tokens, not just final values.
    # Send an empty placeholder message first so that streamed tokens appear incrementally
    # in the UI instead of all at once at the end.
    final_answer = cl.Message(content="")
    await final_answer.send()
    full_content = ""

    async for event in graph.astream_events(
        {"messages": [HumanMessage(content=user_msg.content)]},
        config=config,
    ):
        # We care specifically about chat model token events.
        if event.get("event") == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk is None:
                continue

            delta = getattr(chunk, "content", "") or ""
            if isinstance(delta, str) and delta:
                full_content += delta
                await final_answer.stream_token(delta)

    # Ensure a final message is visible even if nothing streamed, and update the
    # already-sent message with the final content.
    final_answer.content = full_content or "I'm not sure how to respond."
    await final_answer.update()