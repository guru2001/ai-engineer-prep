"""
Chat with streaming support.
"""
from typing import Annotated
from typing_extensions import TypedDict
import operator
from langchain.messages import AnyMessage, HumanMessage, AIMessage, SystemMessage
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END


# Define state
class ChatState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]


# Initialize model
model = init_chat_model("gpt-4o-mini", temperature=0)


def chat_node(state: ChatState):
    """Process chat message and generate response"""
    system_message = SystemMessage(
        content="You are a helpful assistant. Keep responses concise and friendly."
    )
    
    all_messages = [system_message] + state["messages"]
    
    # Get response from model
    response = model.invoke(all_messages)
    
    return {"messages": [response]}


# Build graph
graph = StateGraph(ChatState)
graph.add_node("chat", chat_node)
graph.add_edge(START, "chat")
graph.add_edge("chat", END)

agent = graph.compile()


def chat_stream(message: str = None):
    """Chat interface with streaming"""
    if message is None:
        message = input("You: ")
    
    system_message = SystemMessage(
        content="You are a helpful assistant. Keep responses concise and friendly."
    )
    
    # Stream the response
    print("Assistant: ", end="", flush=True)
    
    # Use astream for streaming
    full_response = ""
    for chunk in model.stream([system_message, HumanMessage(content=message)]):
        if chunk.content:
            print(chunk.content, end="", flush=True)
            full_response += chunk.content
    
    print()  # New line after streaming
    
    return full_response


def chat_with_graph_stream(message: str = None):
    """Chat using graph with streaming"""
    if message is None:
        message = input("You: ")
    
    print("Assistant: ", end="", flush=True)
    
    # Stream from the graph
    full_response = ""
    for chunk in agent.stream({
        "messages": [HumanMessage(content=message)]
    }):
        # Process each chunk
        for node_name, node_output in chunk.items():
            if "messages" in node_output:
                for msg in node_output["messages"]:
                    if isinstance(msg, AIMessage):
                        if msg.content:
                            print(msg.content, end="", flush=True)
                            full_response += msg.content
    
    print()  # New line after streaming
    return full_response


if __name__ == "__main__":
    print("Chat with Streaming")
    print("=" * 40)
    print("Commands:")
    print("  - Type a message to chat (streaming enabled)")
    print("  - Type 'quit' to exit")
    print("=" * 40)
    
    while True:
        user_input = input("\nYou: ").strip()
        
        if user_input.lower() == "quit":
            break
        elif user_input:
            # Use direct model streaming for better streaming experience
            chat_stream(user_input)

