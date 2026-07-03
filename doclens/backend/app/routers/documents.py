from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session, select

from ..config import get_settings
from ..database import get_session
from ..models import Document
from ..schemas import DocumentOut

router = APIRouter(prefix="/api/documents", tags=["documents"])
settings = get_settings()


@router.get("", response_model=list[DocumentOut])
def list_documents(session: Session = Depends(get_session)) -> list[Document]:
    return list(session.exec(select(Document).order_by(Document.created_at.desc())))


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> Document:
    if file.content_type != "application/pdf":
        raise HTTPException(400, "Only PDF files are supported.")

    data = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB limit.")

    doc = Document(
        filename=file.filename or "document.pdf",
        data=data,
        size_bytes=len(data),
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return doc


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: int, session: Session = Depends(get_session)) -> None:
    doc = session.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found.")
    session.delete(doc)
    session.commit()
