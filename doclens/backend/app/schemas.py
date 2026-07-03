from datetime import datetime

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: int
    filename: str
    size_bytes: int
    created_at: datetime


class Citation(BaseModel):
    cited_text: str
    start_page: int | None = None
    end_page: int | None = None


class AskRequest(BaseModel):
    question: str


class AnswerOut(BaseModel):
    answer: str
    citations: list[Citation]


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    citations: list[Citation] = []
    created_at: datetime
