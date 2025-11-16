import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from database import Database
from agent import TodoAgent
from models import Task, TaskCreate, TaskUpdate

app = FastAPI(title="Voice Todo App")

# Initialize database and agent
db = Database()
agent = TodoAgent(db)

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
        response = agent.process_command(command.command)
        # Also get updated task list
        tasks = db.get_all_tasks()
        return JSONResponse({
            "message": response,
            "tasks": [task.model_dump(mode='json') for task in tasks]
        })
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Error in voice-command endpoint: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))


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
