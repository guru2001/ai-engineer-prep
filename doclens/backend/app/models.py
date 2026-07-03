from datetime import datetime, timezone

from sqlalchemy import LargeBinary
from sqlmodel import Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Document(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    filename: str
    # Store the PDF bytes in the DB so the app is stateless — no dependency on
    # a persistent disk, which free hosts (Render/Fly) don't guarantee.
    data: bytes = Field(sa_column=Column(LargeBinary))
    size_bytes: int
    created_at: datetime = Field(default_factory=_utcnow)


class Message(SQLModel, table=True):
    """One turn in a document's Q&A history."""

    id: int | None = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="document.id", index=True)
    role: str  # "user" | "assistant"
    content: str
    # Citations attached to an assistant answer, stored as JSON text.
    citations_json: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
