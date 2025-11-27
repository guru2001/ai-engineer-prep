"""
Chat with web search capability.
"""
from typing import Annotated
from typing_extensions import TypedDict
import operator
from langchain.messages import AnyMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langgraph.graph import StateGraph, START, END
from typing import Literal
from duckduckgo_search import DDGS


@tool
def web_search(query: str) -> str:
    """Search the web for current information.
    
    Args:
        query: The search query
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            
            if not results:
                return "No search results found."
            
            formatted_results = []
            for result in results:
                title = result.get("title", "No title")
                snippet = result.get("body", "No description")
                url = result.get("href", "")
                formatted_results.append(f"Title: {title}\nSnippet: {snippet}\nURL: {url}\n")
            
            return "\n---\n".join(formatted_results)
    except Exception as e:
        return f"Error performing web search: {str(e)}"


# Define tools
tools = [web_search]
tools_by_name = {tool.name: tool for tool in tools}

# Initialize model with tools
model = init_chat_model("gpt-4o-mini", temperature=0)
model_with_tools = model.bind_tools(tools)


# Define state
class WebSearchChatState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]


def llm_node(state: WebSearchChatState):
    """LLM decides whether to search the web or respond"""
    system_message = SystemMessage(
        content="You are a helpful assistant with access to web search. "
                "When users ask about current events, recent information, or things you're not sure about, "
                "use the web_search tool to find up-to-date information. "
                "Be concise and cite your sources when using search results."
    )
    
    all_messages = [system_message] + state["messages"]
    
    response = model_with_tools.invoke(all_messages)
    return {"messages": [response]}


def tool_node(state: WebSearchChatState):
    """Execute tool calls"""
    result = []
    last_message = state["messages"][-1]
    
    for tool_call in last_message.tool_calls:
        tool = tools_by_name[tool_call["name"]]
        print(f"Searching: {tool_call['args'].get('query', 'N/A')}...")
        observation = tool.invoke(tool_call["args"])
        result.append(ToolMessage(
            content=str(observation),
            tool_call_id=tool_call["id"]
        ))
    
    return {"messages": result}


def should_continue(state: WebSearchChatState) -> Literal["tools", END]:
    """Decide whether to call tools or end"""
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END


# Build graph
graph = StateGraph(WebSearchChatState)
graph.add_node("llm", llm_node)
graph.add_node("tools", tool_node)
graph.add_edge(START, "llm")

#After running the llm node, call the function should_continue(state) to decide which edge (next node) to follow.
# “After the llm node runs, ask should_continue where to go.
# If it says tools, go to the tools node.
# If it says END, stop.”
graph.add_conditional_edges(
    "llm",
    should_continue,
    {"tools": "tools", END: END}
)
graph.add_edge("tools", "llm")

agent = graph.compile()


def chat(message: str = None):
    """Chat interface with web search"""
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
            print(f"Search results: {msg.content[:200]}...")


if __name__ == "__main__":
    print("Chat with Web Search")
    print("=" * 40)
    print("Commands:")
    print("  - Ask questions about current events or recent information")
    print("  - The assistant will automatically search the web when needed")
    print("  - Type 'quit' to exit")
    print("=" * 40)
    
    while True:
        user_input = input("\nYou: ").strip()
        
        if user_input.lower() == "quit":
            break
        elif user_input:
            chat(user_input)