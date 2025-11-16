from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskBase(BaseModel):
    title: str
    scheduled_time: Optional[datetime] = None
    priority: Priority = Priority.MEDIUM
    category: Optional[str] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    priority: Optional[Priority] = None
    category: Optional[str] = None


class Task(TaskBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

