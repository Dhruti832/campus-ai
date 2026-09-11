"""The /chat endpoint. Rate-limited per-IP so the shared Groq quota on
the live demo can't be exhausted by one client (see build plan section 3).

Deliberately does NOT use ``from __future__ import annotations``: FastAPI
resolves Pydantic model annotations at runtime, and postponed evaluation
breaks that resolution once slowapi's @limiter.limit decorator wraps the
endpoint function.
"""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.chat_engine import get_reply
from app.config import get_active_corpus_config
from app.db.session import get_db
from app.rate_limit import limiter

router = APIRouter()


class ChatRequest(BaseModel):
    query: str = Field(min_length=1)
    category_filter: str | None = None
    top_k: int | None = None


class SourceOut(BaseModel):
    url: str
    title: str
    category: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceOut]


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
def chat(
    request: Request, body: ChatRequest, db: Session = Depends(get_db)  # noqa: B008
) -> ChatResponse:
    corpus_config = get_active_corpus_config()
    reply = get_reply(
        session=db,
        corpus_config=corpus_config,
        query=body.query,
        top_k=body.top_k,
        category_filter=body.category_filter,
    )
    return ChatResponse(answer=reply["text"], sources=reply["sources"])
