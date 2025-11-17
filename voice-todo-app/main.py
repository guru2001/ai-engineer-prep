from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from database import Database
from agent import TodoAgent
from models import Task, TaskCreate, TaskUpdate
from logger_config import logger

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("Loaded environment variables from .env file")
except ImportError:
    # python-dotenv not installed, skip .env loading
    pass

app = FastAPI(title="Voice Todo App")

# Initialize database and agent
logger.info("Initializing application...")
try:
    db = Database()
    agent = TodoAgent(db)
    logger.info("Application initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize application: {e}", exc_info=True)
    raise

# Initialize Deepgram service (required)
from deepgram_service import DeepgramService
try:
    deepgram_service = DeepgramService()
    logger.info("Deepgram service initialized")
except Exception as e:
    logger.error(f"Failed to initialize Deepgram service: {e}", exc_info=True)
    raise ValueError("Deepgram service is required. Please set DEEPGRAM_API_KEY environment variable.")

# Mount static files (for frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")


class VoiceCommand(BaseModel):
    command: str
    session_id: str = "default"
    chat_history: list[dict] = None


class TaskResponse(BaseModel):
    tasks: list[Task]
    message: str


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page"""
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())


@app.post("/api/voice-command")
async def process_voice_command(command: VoiceCommand):
    """Process a voice command using the LangChain agent"""
    try:
        if not command.command or not command.command.strip():
            raise HTTPException(status_code=400, detail="Command cannot be empty")
        
        logger.info(f"Received voice command: {command.command} (session: {command.session_id})")
        response = agent.process_command(
            command.command, 
            session_id=command.session_id,
            chat_history=command.chat_history
        )
        # Also get updated task list (filtered by session_id)
        tasks = db.get_all_tasks(session_id=command.session_id)
        # Get updated chat history
        chat_history = agent.get_chat_history(command.session_id)
        logger.info(f"Command processed successfully, returning {len(tasks)} tasks")
        return JSONResponse({
            "message": response,
            "tasks": [task.model_dump(mode='json') for task in tasks],
            "chat_history": chat_history
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in voice-command endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error processing command")


@app.post("/api/transcribe-audio")
async def transcribe_audio(audio: UploadFile = File(...), language: str = "en", 
                          session_id: str = "default", chat_history: str = None):
    """Transcribe audio file using Deepgram API
    
    Args:
        audio: Audio file (supports: mp3, wav, webm, ogg, flac, m4a, mp4, and more)
        language: Language code (optional, auto-detects if not provided)
        session_id: Session ID for chat history
        chat_history: JSON string of chat history (optional)
    """
    try:
        # Read file content
        file_content = await audio.read()
        
        # Create a file-like object for Deepgram
        import io
        import json
        audio_file = io.BytesIO(file_content)
        
        logger.info(f"Transcribing audio file: {audio.filename or 'unknown'} (language: {language or 'auto-detect'}, session: {session_id})")
        
        # Transcribe using Deepgram
        transcript = deepgram_service.transcribe_audio(audio_file, language=language if language else None)
        
        # Parse chat history if provided
        history = None
        if chat_history:
            try:
                history = json.loads(chat_history)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse chat_history: {chat_history}")
        
        # Process the transcribed command
        response = agent.process_command(transcript, session_id=session_id, chat_history=history)
        tasks = db.get_all_tasks(session_id=session_id)
        # Get updated chat history
        updated_history = agent.get_chat_history(session_id)
        
        logger.info(f"Audio transcribed and processed successfully")
        return JSONResponse({
            "transcript": transcript,
            "message": response,
            "tasks": [task.model_dump(mode='json') for task in tasks],
            "chat_history": updated_history
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error transcribing audio: {str(e)}")




@app.get("/api/tasks", response_model=TaskResponse)
async def get_tasks(category: str = None, session_id: str = "default"):
    """Get all tasks, optionally filtered by category and session_id"""
    tasks = db.get_all_tasks(category=category, session_id=session_id)
    return TaskResponse(tasks=tasks, message=f"Found {len(tasks)} task(s)")


@app.post("/api/tasks", response_model=Task)
async def create_task(task: TaskCreate, session_id: str = "default"):
    """Create a new task"""
    return db.create_task(task, session_id=session_id)


@app.put("/api/tasks/{task_id}", response_model=Task)
async def update_task(task_id: int, task: TaskUpdate, session_id: str = "default"):
    """Update a task"""
    updated = db.update_task(task_id, task, session_id=session_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int, session_id: str = "default"):
    """Delete a task"""
    success = db.delete_task(task_id, session_id=session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully"}


@app.get("/api/chat-history")
async def get_chat_history(session_id: str = "default"):
    """Get chat history for a session"""
    history = agent.get_chat_history(session_id)
    return JSONResponse({"chat_history": history})


@app.delete("/api/chat-history")
async def clear_chat_history(session_id: str = "default"):
    """Clear chat history for a session"""
    agent.clear_chat_history(session_id)
    return JSONResponse({"message": f"Chat history cleared for session: {session_id}"})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
