# Voice Todo App

A voice-first to-do list web application that uses natural language voice commands to perform CRUD operations on tasks. Built with FastAPI, LangChain, and Web Speech API.

## Features

- 🎤 **Voice Commands**: Speak naturally to create, update, delete, and list tasks
- 🤖 **LangChain Agent**: Intelligent natural language processing for understanding commands
- 📝 **Task Management**: Tasks with title, priority, scheduled time, and category
- 🔊 **Text-to-Speech**: Audio feedback for all actions
- 💾 **SQLite Database**: Persistent storage for your tasks

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
pip install fastapi uvicorn langchain langchain-openai langchain-community pydantic python-dateutil
```

### 2. Set OpenAI API Key

The app uses OpenAI's GPT models via LangChain. Set your API key:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

Or create a `.env` file:
```
OPENAI_API_KEY=your-api-key-here
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

## Browser Requirements

- Chrome, Edge, or Safari (for Web Speech API support)
- Microphone permissions enabled
- HTTPS (or localhost) for speech recognition to work

## Project Structure

```
voice-todo-app/
├── main.py           # FastAPI application and routes
├── agent.py          # LangChain agent for processing commands
├── database.py       # SQLite database operations
├── models.py         # Pydantic models for tasks
├── static/
│   └── index.html    # Frontend with voice controls
└── todos.db          # SQLite database (created automatically)
```

## API Endpoints

- `GET /` - Main web interface
- `POST /api/voice-command` - Process voice command
- `GET /api/tasks` - Get all tasks (optional `?category=...`)
- `POST /api/tasks` - Create a new task
- `PUT /api/tasks/{task_id}` - Update a task
- `DELETE /api/tasks/{task_id}` - Delete a task

## Notes

- The app uses Web Speech API for speech-to-text (browser-based, free)
- Text-to-speech uses the browser's built-in SpeechSynthesis API
- Tasks are stored in a local SQLite database
- The LangChain agent uses OpenAI's GPT-4o-mini model (cost-effective)

