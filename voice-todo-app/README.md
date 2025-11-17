# Voice Todo App

A voice-first to-do list web application that uses natural language voice commands to perform CRUD operations on tasks. Built with FastAPI, LangChain, and Web Speech API.

## Features

- 🎤 **Voice Commands**: Speak naturally to create, update, delete, and list tasks
- 🤖 **LangChain Agent**: Intelligent natural language processing for understanding commands
- 📝 **Task Management**: Tasks with title, priority, scheduled time, and category
- 🔊 **Text-to-Speech**: Audio feedback for all actions
- 🔍 **ChromaDB Vector Database**: Semantic search capabilities for finding tasks by meaning
- 💾 **Persistent Storage**: Local ChromaDB storage for your tasks
- 🔐 **Session Isolation**: Each user session maintains separate tasks and chat history

## Example Commands

- "Show me all administrative tasks"
- "Create a task to fix bugs"
- "Make me a task to do grocery shopping"
- "Delete the task about compliances"
- "Push the task about fixing bugs to tomorrow"
- "Delete the 4th task"
- "Update the task about meetings to high priority"

## Setup

### 1. Install Dependencies

```bash
pip install -e .
```

Or install manually:
```bash
pip install fastapi uvicorn langchain langchain-openai langchain-community pydantic python-dateutil chromadb openai
```

### 2. Set API Keys

The app requires two API keys:

**OpenAI API Key** (required):
- Used for GPT models via LangChain and OpenAI embeddings for semantic search

**Deepgram API Key** (required):
- Used for speech-to-text transcription

Set your API keys:

```bash
export OPENAI_API_KEY="your-api-key-here"
export DEEPGRAM_API_KEY="your-deepgram-api-key-here"
```

Or create a `.env` file:
```
OPENAI_API_KEY=your-api-key-here
DEEPGRAM_API_KEY=your-deepgram-api-key-here
```

### 3. Run the Application

```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload
```

The app will be available at `http://localhost:8000`

## Usage

1. Open your browser and navigate to `http://localhost:8000`
2. Click the "Start Speaking" button
3. Speak your command naturally
4. The app will process your command and update the task list
5. You'll hear an audio confirmation of the action

## Sessions

The app uses **session-based isolation** to ensure each user's tasks and chat history remain separate:

### How Sessions Work

- **Automatic Session Creation**: When you first visit the app, a unique session ID is automatically generated and stored in your browser's localStorage
- **Session Persistence**: Your session ID persists across page refreshes, so your tasks remain accessible
- **Task Isolation**: Each session maintains its own set of tasks with independent task IDs (starting from 1 per session)
- **Chat History**: Each session has its own conversation history (last 20 messages) that helps the agent understand context from previous interactions
- **Agent Isolation**: Each session has its own LangChain agent instance, ensuring personalized responses

### Session Benefits

- **Multi-User Support**: Multiple users can use the app simultaneously without interfering with each other's tasks
- **Context Awareness**: The agent remembers your previous commands within a session, enabling more natural conversations
- **Privacy**: Tasks are isolated per session, providing data privacy between different users or browser sessions

### Technical Details

- Session IDs are generated using `crypto.randomUUID()` (or a fallback method if unavailable)
- Tasks are stored with composite IDs: `{session_id}_{task_id}` in ChromaDB
- All API endpoints accept an optional `session_id` parameter (defaults to "default" for backward compatibility)
- Chat history is maintained in memory per session and limited to the last 20 messages to manage token usage

## Browser Requirements

- Chrome, Edge, or Safari (for Web Speech API support)
- Microphone permissions enabled
- HTTPS (or localhost) for speech recognition to work

## Project Structure

```
voice-todo-app/
├── main.py           # FastAPI application and routes
├── agent.py          # LangChain agent for processing commands
├── database.py       # ChromaDB database operations
├── models.py         # Pydantic models for tasks
├── static/
│   └── index.html    # Frontend with voice controls
└── chroma_db/        # ChromaDB storage directory (created automatically)
```

## API Endpoints

- `GET /` - Main web interface
- `POST /api/voice-command` - Process voice command (accepts `session_id` in request body)
- `POST /api/transcribe-audio` - Transcribe audio file using Deepgram (accepts `session_id` parameter)
- `GET /api/tasks` - Get all tasks (optional `?category=...&session_id=...`)
- `POST /api/tasks` - Create a new task (accepts `session_id` in request body)
- `PUT /api/tasks/{task_id}` - Update a task (accepts `session_id` in request body)
- `DELETE /api/tasks/{task_id}` - Delete a task (accepts `session_id` in request body)

**Note**: All endpoints support an optional `session_id` parameter. If not provided, it defaults to `"default"` for backward compatibility.

## Notes

- The app uses Deepgram API for speech-to-text transcription (supports multiple audio formats)
- Text-to-speech uses the browser's built-in SpeechSynthesis API
- Tasks are stored in a local ChromaDB vector database for semantic search
- The LangChain agent uses OpenAI's GPT-4o-mini model (cost-effective)
- Embeddings are generated using OpenAI's text-embedding-3-small model
- Semantic search allows finding tasks by meaning, not just keywords (e.g., "meetings" finds "team sync", "standup", etc.)
- Session isolation ensures tasks and chat history are separated per user session
- The app maintains backward compatibility with tasks created before session support was added

