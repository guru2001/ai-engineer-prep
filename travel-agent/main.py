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

from city_extractor import extract_places_from_text
from map_utils import get_map_urls

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
    
    # Extract places from the response and display map in sidebar
    if full_content:
        places = extract_places_from_text(full_content, model=model)
        
        if places:
            # Limit to 10 places
            places = places[:10]
            
            # Get map URLs
            embed_url, map_url = get_map_urls(places)
            
            # Debug: print URLs to verify they're generated
            print(f"Map URLs - Embed: {embed_url[:100] if embed_url else 'None'}..., Regular: {map_url[:100] if map_url else 'None'}...")
            print(f"Places to pass: {places}")
            print(f"Map URL: {map_url}")
            print(f"Embed URL: {embed_url}")
            
            # Extract place names for display
            place_names = [place.name if hasattr(place, "name") else str(place) for place in places]
            
            # Create CustomElement for the map
            # Pass place names array for backward compatibility with TripMap component
            try:
                props = {
                    "cities": place_names,  # Keep "cities" key for backward compatibility with TripMap component
                    "mapUrl": map_url or "",
                    "embed_url": embed_url or ""
                }
                print("props ", props)
                map_element = cl.CustomElement(
                    name="TripMap",
                    props=props
                )
                
                # Display the map in the sidebar using ElementSidebar API
                await cl.ElementSidebar.set_title("Trip Map")
                await cl.ElementSidebar.set_elements([map_element], key="trip-map")
                
                # Also send a message to notify the user
                map_message = cl.Message(
                    content=f"🗺️ **Trip Map** - Visiting {len(places)} places: {', '.join(place_names)}\n\nThe map is now displayed in the sidebar!"
                )
                await map_message.send()
            except Exception as e:
                # Fallback: send a message with just the link if CustomElement fails
                print(f"Error creating CustomElement: {e}")
                fallback_message = cl.Message(
                    content=f"🗺️ **Trip Map** - Visiting {len(places)} places: {', '.join(place_names)}\n\n[Open in Google Maps]({map_url})"
                )
                await fallback_message.send()