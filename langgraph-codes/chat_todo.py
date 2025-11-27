"""
Basic chat with todo list functionality.
"""
from typing import Annotated
from typing_extensions import TypedDict
import operator
import json
from langchain.messages import AnyMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langgraph.graph import StateGraph, START, END
from typing import Literal


# In-memory todo storage
todos: list[dict] = []


@tool
def add_todo(task: str) -> str:
    """Add a new todo item.
    
    Args:
        task: The task description to add
    """
    todo = {
        "id": len(todos) + 1,
        "task": task,
        "completed": False
    }
    todos.append(todo)
    return f"Added todo: {task} (ID: {todo['id']})"


@tool
def list_todos() -> str:
    """List all todo items."""
    if not todos:
        return "No todos found."
    
    result = "Todo List:\n"
    for todo in todos:
        status = "✓" if todo["completed"] else "○"
        result += f"{status} [{todo['id']}] {todo['task']}\n"
    return result.strip()


@tool
def complete_todo(todo_id: int) -> str:
    """Mark a todo item as completed.
    
    Args:
        todo_id: The ID of the todo to complete
    """
    for todo in todos:
        if todo["id"] == todo_id:
            todo["completed"] = True
            return f"Completed todo: {todo['task']}"
    return f"Todo with ID {todo_id} not found."


@tool
def delete_todo(todo_id: int) -> str:
    """Delete a todo item.
    
    Args:
        todo_id: The ID of the todo to delete
    """
    global todos
    for i, todo in enumerate(todos):
        if todo["id"] == todo_id:
            task = todo["task"]
            todos.pop(i)
            return f"Deleted todo: {task}"
    return f"Todo with ID {todo_id} not found."


# Define tools
tools = [add_todo, list_todos, complete_todo, delete_todo]
tools_by_name = {tool.name: tool for tool in tools}

# Initialize model with tools
model = init_chat_model("gpt-4o-mini", temperature=0)
model_with_tools = model.bind_tools(tools)


# Define state
class TodoChatState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]


def llm_node(state: TodoChatState):
    """LLM decides whether to call a tool or respond"""
    system_message = SystemMessage(
        content="You are a helpful assistant that manages a todo list. "
                "When users ask about todos, use the appropriate tools. "
                "Be friendly and helpful."
    )
    
    all_messages = [system_message] + state["messages"]
    
    response = model_with_tools.invoke(all_messages)
    return {"messages": [response]}


def tool_node(state: TodoChatState):
    """Execute tool calls"""
    result = []
    last_message = state["messages"][-1]
    
    for tool_call in last_message.tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        result.append(ToolMessage(
            content=str(observation),
            tool_call_id=tool_call["id"]
        ))
    
    return {"messages": result}


def should_continue(state: TodoChatState) -> Literal["tools", END]:
    """Decide whether to call tools or end"""
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END


# Build graph
graph = StateGraph(TodoChatState)
graph.add_node("llm", llm_node)
graph.add_node("tools", tool_node)
graph.add_edge(START, "llm")
graph.add_conditional_edges(
    "llm",
    should_continue,
    {"tools": "tools", END: END}
)
graph.add_edge("tools", "llm")

agent = graph.compile()


def chat(message: str = None):
    """Chat interface with todo list"""
    if message is None:
        message = input("You: ")
    
    result = agent.invoke({
        "messages": [HumanMessage(content=message)]
    })
    
    # Get the last AI message
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            print(f"Assistant: {msg.content}")
            return msg.content
    
    # If no direct response, show tool results
    for msg in result["messages"]:
        if isinstance(msg, ToolMessage):
            print(f"Tool: {msg.content}")


if __name__ == "__main__":
    print("Chat with Todo List")
    print("=" * 40)
    print("Commands:")
    print("  - 'add todo: <task>' - Add a new todo")
    print("  - 'list todos' - List all todos")
    print("  - 'complete todo <id>' - Complete a todo")
    print("  - 'delete todo <id>' - Delete a todo")
    print("  - Or just chat naturally!")
    print("  - Type 'quit' to exit")
    print("=" * 40)
    
    while True:
        user_input = input("\nYou: ").strip()
        
        if user_input.lower() == "quit":
            break
        elif user_input:
            chat(user_input)

