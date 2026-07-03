import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models import Document, Message
from ..schemas import AnswerOut, AskRequest, Citation, MessageOut
from ..services.llm import answer_question

router = APIRouter(prefix="/api/documents/{document_id}", tags=["chat"])


def _load_pdf(document_id: int, session: Session) -> Document:
    doc = session.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found.")
    return doc


@router.get("/messages", response_model=list[MessageOut])
def history(document_id: int, session: Session = Depends(get_session)) -> list[MessageOut]:
    _load_pdf(document_id, session)
    rows = session.exec(
        select(Message).where(Message.document_id == document_id).order_by(Message.created_at)
    )
    out: list[MessageOut] = []
    for m in rows:
        citations = [Citation(**c) for c in json.loads(m.citations_json)] if m.citations_json else []
        out.append(
            MessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                citations=citations,
                created_at=m.created_at,
            )
        )
    return out


@router.post("/ask", response_model=AnswerOut)
def ask(
    document_id: int,
    body: AskRequest,
    session: Session = Depends(get_session),
) -> AnswerOut:
    doc = _load_pdf(document_id, session)
    question = body.question.strip()
    if not question:
        raise HTTPException(400, "Question must not be empty.")

    answer, raw_citations = answer_question(doc.data, doc.filename, question)
    citations = [Citation(**c) for c in raw_citations]

    session.add(Message(document_id=document_id, role="user", content=question))
    session.add(
        Message(
            document_id=document_id,
            role="assistant",
            content=answer,
            citations_json=json.dumps(raw_citations),
        )
    )
    session.commit()

    return AnswerOut(answer=answer, citations=citations)
