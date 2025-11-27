# LangGraph Chat Examples

This repository contains various chat implementations using LangGraph, demonstrating different capabilities and patterns.

## Features

### 1. Basic Chat with Threads (In-Memory)
**File:** `chat_threads_memory.py`

A simple chat implementation with thread/conversation management using in-memory storage. Each thread maintains its own conversation history.

**Usage:**
```bash
python chat_threads_memory.py
```

**Features:**
- Multiple conversation threads
- Thread isolation (each thread has its own history)
- Simple in-memory storage
- Commands: `new` (new thread), `threads` (list threads), `quit` (exit)

### 2. Basic Chat with Threads (PostgreSQL)
**File:** `chat_threads_postgres.py`

Same as above but with PostgreSQL persistence. Threads and messages are stored in a database.

**Setup:**
```bash
# Set database URL
export DATABASE_URL='postgresql://user:password@localhost/dbname'

# Or create a local database
createdb langgraph_chat
export DATABASE_URL='postgresql://localhost/langgraph_chat'
```

**Usage:**
```bash
python chat_threads_postgres.py
```

**Features:**
- Persistent storage in PostgreSQL
- Automatic table creation
- Thread and message history persistence
- Same commands as in-memory version

### 3. Chat with Todo List
**File:** `chat_todo.py`

A chat assistant that can manage a todo list. The assistant can add, list, complete, and delete todos using tools.

**Usage:**
```bash
python chat_todo.py
```

**Features:**
- Add todos: "add todo: Buy groceries"
- List todos: "list todos" or "show my todos"
- Complete todos: "complete todo 1"
- Delete todos: "delete todo 1"
- Natural language interaction

### 4. Chat with Streaming
**File:** `chat_stream.py`

A chat implementation with streaming responses for real-time output.

**Usage:**
```bash
python chat_stream.py
```

**Features:**
- Real-time streaming of responses
- Character-by-character output
- Better user experience for longer responses

### 5. Chat with Web Search
**File:** `chat_websearch.py`

A chat assistant with web search capabilities using DuckDuckGo. Automatically searches the web when needed.

**Usage:**
```bash
python chat_websearch.py
```

**Features:**
- Automatic web search for current information
- Up-to-date information retrieval
- Source citations in responses
- Ask about current events, recent news, etc.

**Example queries:**
- "What's the latest news about AI?"
- "What is the current weather in San Francisco?"
- "Tell me about recent developments in quantum computing"

### 6. Chat with Code Interpreter
**File:** `chat_code_interpreter.py`

A chat assistant that can execute Python code for calculations, data analysis, and more.

**Usage:**
```bash
python chat_code_interpreter.py
```

**Features:**
- Execute Python code
- Perform calculations
- Data analysis and manipulation
- Expression evaluation

**Example queries:**
- "Calculate 15 * 23 + 45"
- "Create a list of numbers 1-10 and calculate their sum"
- "What is 2 to the power of 8?"

**⚠️ Warning:** This executes arbitrary Python code. Use responsibly!

## Installation

1. Install dependencies:
```bash
uv sync
# or
pip install -e .
```

2. Set up environment variables (if needed):
```bash
# For PostgreSQL chat
export DATABASE_URL='postgresql://user:password@localhost/dbname'

# For OpenAI (if not using default)
export OPENAI_API_KEY='your-api-key'
```

## Dependencies

- `langchain` - LangChain framework
- `langchain-openai` - OpenAI integration
- `langgraph` - LangGraph for building agent workflows
- `psycopg2-binary` - PostgreSQL adapter (for PostgreSQL chat)
- `duckduckgo-search` - Web search (for web search chat)
- `langchain-community` - Additional LangChain tools

## Calculator Example

The repository also includes a calculator example (`calculator.py`) that demonstrates basic tool usage with LangGraph.

## Architecture

All chat implementations follow a similar pattern:

1. **State Definition**: Define the state structure using TypedDict
2. **Node Functions**: Define nodes for LLM calls and tool execution
3. **Graph Construction**: Build the graph with nodes and edges
4. **Conditional Routing**: Use conditional edges to route based on tool calls
5. **Compilation**: Compile the graph into an executable agent

## License

MIT

