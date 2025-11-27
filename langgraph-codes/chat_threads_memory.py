"""
Basic chat with threads using in-memory storage.
"""
from typing import Annotated
from typing_extensions import TypedDict
import operator
from langchain.messages import AnyMessage, HumanMessage, AIMessage, SystemMessage
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END


# In-memory thread storage
class ThreadStore:
    def __init__(self):
        self.threads: dict[str, list[AnyMessage]] = {}
    
    def get_thread(self, thread_id: str) -> list[AnyMessage]:
        """Get messages for a thread"""
        return self.threads.get(thread_id, [])
    
    def add_message(self, thread_id: str, message: AnyMessage):
        """Add a message to a thread"""
        if thread_id not in self.threads:
            self.threads[thread_id] = []
        self.threads[thread_id].append(message)
    
    def get_all_threads(self) -> list[str]:
        """Get all thread IDs"""
        return list(self.threads.keys())


# Global thread store
thread_store = ThreadStore()


# Define state
class ChatState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    thread_id: str


# Initialize model
model = init_chat_model("gpt-4o-mini", temperature=0)


def chat_node(state: ChatState):
    """Process chat message and generate response"""
    thread_id = state.get("thread_id", "default")
    
    # Get conversation history from thread store
    history = thread_store.get_thread(thread_id)
    
    # Combine history with new messages
    all_messages = history + state["messages"]
    
    # Add system message if not present
    if not all_messages or not isinstance(all_messages[0], SystemMessage):
        system_msg = SystemMessage(
            content="You are a helpful assistant. Keep responses concise and friendly."
        )
        all_messages = [system_msg] + all_messages
    
    # Get response from model
    response = model.invoke(all_messages)
    
    # Store messages in thread
    for msg in state["messages"]:
        thread_store.add_message(thread_id, msg)
    thread_store.add_message(thread_id, response)
    
    return {"messages": [response]}


# Build graph
graph = StateGraph(ChatState)
graph.add_node("chat", chat_node)
graph.add_edge(START, "chat")
graph.add_edge("chat", END)

agent = graph.compile()


def chat(thread_id: str = "default", message: str = None):
    """Chat interface"""
    if message is None:
        message = input("You: ")
    
    result = agent.invoke({
        "messages": [HumanMessage(content=message)],
        "thread_id": thread_id
    })
    
    response = result["messages"][-1].content
    print(f"Assistant: {response}")
    return response


if __name__ == "__main__":
    print("Chat with Threads (In-Memory)")
    print("=" * 40)
    print("Commands:")
    print("  - Type a message to chat")
    print("  - Type 'new' to start a new thread")
    print("  - Type 'threads' to list all threads")
    print("  - Type 'quit' to exit")
    print("=" * 40)
    
    current_thread = "default"
    
    while True:
        user_input = input(f"\n[{current_thread}] You: ").strip()
        
        if user_input.lower() == "quit":
            break
        elif user_input.lower() == "new":
            import uuid
            current_thread = str(uuid.uuid4())[:8]
            print(f"Started new thread: {current_thread}")
        elif user_input.lower() == "threads":
            threads = thread_store.get_all_threads()
            print(f"Active threads: {threads}")
        elif user_input:
            chat(current_thread, user_input)

