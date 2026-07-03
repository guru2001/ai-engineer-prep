"""LLM integration for grounded, cited document Q&A — Google Gemini (free tier).

Gemini reads the PDF directly (no embeddings / vector DB). We use Gemini's
structured-output mode to get back a typed JSON object: the answer plus a list
of citations, each carrying the quoted passage and the page it came from.
"""

from functools import lru_cache

from google import genai
from google.genai import types
from pydantic import BaseModel

from ..config import get_settings

SYSTEM_PROMPT = (
    "You are DocLens, a careful document analyst. Answer the user's question "
    "using ONLY the attached document. For every claim, include a citation with "
    "the exact quoted passage and the page number it appears on. If the answer is "
    "not in the document, say so plainly rather than guessing, and return no "
    "citations."
)


class _Citation(BaseModel):
    cited_text: str
    start_page: int | None = None
    end_page: int | None = None


class _CitedAnswer(BaseModel):
    answer: str
    citations: list[_Citation]


@lru_cache
def _client() -> genai.Client:
    # Reads GEMINI_API_KEY / GOOGLE_API_KEY from the environment.
    return genai.Client()


def answer_question(pdf_bytes: bytes, filename: str, question: str) -> tuple[str, list[dict]]:
    """Return (answer_text, citations) for a question about a PDF."""
    settings = get_settings()

    response = _client().models.generate_content(
        model=settings.gemini_model,
        contents=[
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
            f"Document title: {filename}\n\nQuestion: {question}",
        ],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=_CitedAnswer,
            max_output_tokens=2048,
        ),
    )

    parsed: _CitedAnswer | None = getattr(response, "parsed", None)
    if parsed is None:  # fall back to parsing the JSON text if needed
        parsed = _CitedAnswer.model_validate_json(response.text)

    citations = [c.model_dump() for c in parsed.citations]
    return parsed.answer.strip(), citations
