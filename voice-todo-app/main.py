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
        
        logger.info(f"Received voice command: {command.command}")
        response = agent.process_command(command.command)
        # Also get updated task list
        tasks = db.get_all_tasks()
        logger.info(f"Command processed successfully, returning {len(tasks)} tasks")
        return JSONResponse({
            "message": response,
            "tasks": [task.model_dump(mode='json') for task in tasks]
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in voice-command endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error processing command")


@app.post("/api/transcribe-audio")
async def transcribe_audio(audio: UploadFile = File(...), language: str = "en"):
    """Transcribe audio file using Deepgram API
    
    Args:
        audio: Audio file (supports: mp3, wav, webm, ogg, flac, m4a, mp4, and more)
        language: Language code (optional, auto-detects if not provided)
    """
    try:
        # Read file content
        file_content = await audio.read()
        
        # Create a file-like object for Deepgram
        import io
        audio_file = io.BytesIO(file_content)
        
        logger.info(f"Transcribing audio file: {audio.filename or 'unknown'} (language: {language or 'auto-detect'})")
        
        # Transcribe using Deepgram
        transcript = deepgram_service.transcribe_audio(audio_file, language=language if language else None)
        
        # Process the transcribed command
        response = agent.process_command(transcript)
        tasks = db.get_all_tasks()
        
        logger.info(f"Audio transcribed and processed successfully")
        return JSONResponse({
            "transcript": transcript,
            "message": response,
            "tasks": [task.model_dump(mode='json') for task in tasks]
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error transcribing audio: {str(e)}")




@app.get("/api/tasks", response_model=TaskResponse)
async def get_tasks(category: str = None):
    """Get all tasks, optionally filtered by category"""
    tasks = db.get_all_tasks(category=category)
    return TaskResponse(tasks=tasks, message=f"Found {len(tasks)} task(s)")


@app.post("/api/tasks", response_model=Task)
async def create_task(task: TaskCreate):
    """Create a new task"""
    return db.create_task(task)


@app.put("/api/tasks/{task_id}", response_model=Task)
async def update_task(task_id: int, task: TaskUpdate):
    """Update a task"""
    updated = db.update_task(task_id, task)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int):
    """Delete a task"""
    success = db.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
