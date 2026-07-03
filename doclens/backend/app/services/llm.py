"""LLM integration for grounded, cited document Q&A — OpenAI.

We extract the PDF's text page by page and label each page (`=== Page N ===`),
then ask the model — via OpenAI structured outputs — to answer using only that
text and cite the exact passage plus the page it came from. Labeling pages
ourselves makes the citations' page numbers exact rather than model-guessed.
"""

import io
from functools import lru_cache

from openai import OpenAI
from pydantic import BaseModel
from pypdf import PdfReader

from ..config import get_settings

SYSTEM_PROMPT = (
    "You are DocLens, a careful document analyst. Answer the user's question "
    "using ONLY the provided document text. The document is split into sections "
    "marked '=== Page N ==='. For every claim, add a citation with the exact "
    "quoted passage and the page number (N) it appears on. If the answer is not "
    "in the document, say so plainly and return no citations."
)


class _Citation(BaseModel):
    cited_text: str
    start_page: int | None = None
    end_page: int | None = None


class _CitedAnswer(BaseModel):
    answer: str
    citations: list[_Citation]


@lru_cache
def _client() -> OpenAI:
    # Reads OPENAI_API_KEY from the environment.
    return OpenAI()


def _extract_pages(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    parts: list[str] = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            parts.append(f"=== Page {i} ===\n{text}")
    return "\n\n".join(parts)


def answer_question(pdf_bytes: bytes, filename: str, question: str) -> tuple[str, list[dict]]:
    """Return (answer_text, citations) for a question about a PDF."""
    settings = get_settings()

    doc_text = _extract_pages(pdf_bytes)
    if not doc_text:
        return (
            "I couldn't extract any text from this PDF — it may be a scanned image "
            "without a text layer.",
            [],
        )

    user_content = f"Document: {filename}\n\n{doc_text}\n\n---\nQuestion: {question}"

    completion = _client().beta.chat.completions.parse(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format=_CitedAnswer,
    )

    message = completion.choices[0].message
    if message.refusal:
        return message.refusal, []

    parsed = message.parsed
    if parsed is None:
        return "The model returned no answer. Please try rephrasing.", []

    citations = [c.model_dump() for c in parsed.citations]
    return parsed.answer.strip(), citations
