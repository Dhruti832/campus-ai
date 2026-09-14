"""The /chat endpoint. Rate-limited per-IP so the shared Groq quota on
the live demo can't be exhausted by one client (see build plan section 3).

Deliberately does NOT use ``from __future__ import annotations``: FastAPI
resolves Pydantic model annotations at runtime, and postponed evaluation
breaks that resolution once slowapi's @limiter.limit decorator wraps the
endpoint function.
"""

import json
from typing import Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.admin_service import resolve_active_corpus_config
from app.agent.chat_engine import get_reply, prepare_reply_context, stream_reply_events
from app.db.models import Feedback
from app.db.session import get_db
from app.llm.factory import get_llm_provider
from app.llm.prompt_builder import HistoryTurn
from app.rate_limit import limiter

router = APIRouter()


class HistoryTurnIn(BaseModel):
    role: Literal["user", "assistant"]
    text: str


class ChatRequest(BaseModel):
    query: str = Field(min_length=1)
    category_filter: str | None = None
    top_k: int | None = None
    # Prior turns in the conversation, oldest first — lets follow-up
    # questions ("what about X") make sense to the LLM. Trimmed to the last
    # few turns in build_prompt() regardless of how much is sent here.
    history: list[HistoryTurnIn] = Field(default_factory=list)


class SourceOut(BaseModel):
    url: str
    title: str
    category: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceOut]


class ActiveCorpusResponse(BaseModel):
    name: str
    description: str


class FeedbackRequest(BaseModel):
    query: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    rating: Literal[-1, 1]


class FeedbackResponse(BaseModel):
    ok: bool = True


@router.get("/active-corpus", response_model=ActiveCorpusResponse)
def active_corpus(db: Session = Depends(get_db)) -> ActiveCorpusResponse:  # noqa: B008
    """Public (no admin key) — just enough to show the user which corpus
    they're actually talking to. The chat UI has no other way to tell,
    since the frontend never loads corpus configs itself."""
    corpus_config = resolve_active_corpus_config(db)
    return ActiveCorpusResponse(name=corpus_config.name, description=corpus_config.description)


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
def chat(
    request: Request, body: ChatRequest, db: Session = Depends(get_db)  # noqa: B008
) -> ChatResponse:
    corpus_config = resolve_active_corpus_config(db)
    reply = get_reply(
        session=db,
        corpus_config=corpus_config,
        query=body.query,
        top_k=body.top_k,
        category_filter=body.category_filter,
        history=[HistoryTurn(role=h.role, text=h.text) for h in body.history],
    )
    return ChatResponse(answer=reply["text"], sources=reply["sources"])


@router.post("/chat/stream")
@limiter.limit("20/minute")
def chat_stream(
    request: Request, body: ChatRequest, db: Session = Depends(get_db)  # noqa: B008
) -> StreamingResponse:
    """Newline-delimited JSON stream: one ``{"type": "token", "text": ...}``
    object per chunk of the answer, followed by a final
    ``{"type": "sources", "sources": [...]}`` object. NDJSON over a plain
    POST rather than text/event-stream, since native EventSource can't send
    a POST body — the frontend reads this with a plain fetch + ReadableStream
    reader, matching the project's hand-rolled-over-framework approach.

    All DB access happens above, before this function returns — see
    prepare_reply_context's docstring for why that split is required.
    """
    corpus_config = resolve_active_corpus_config(db)
    shortcut, results = prepare_reply_context(
        db,
        corpus_config,
        body.query,
        top_k=body.top_k,
        category_filter=body.category_filter,
    )
    llm_provider = get_llm_provider()
    history = [HistoryTurn(role=h.role, text=h.text) for h in body.history]

    def event_source():
        events = stream_reply_events(
            body.query, corpus_config, shortcut, results, llm_provider, history=history
        )
        for event in events:
            yield json.dumps(event) + "\n"

    return StreamingResponse(event_source(), media_type="application/x-ndjson")


@router.post("/feedback", response_model=FeedbackResponse)
@limiter.limit("30/minute")
def feedback(
    request: Request, body: FeedbackRequest, db: Session = Depends(get_db)  # noqa: B008
) -> FeedbackResponse:
    """Thumbs up/down on an answer. The corpus is resolved server-side
    (same as /chat) rather than trusted from the client, since a caller
    could otherwise attribute feedback to a corpus they never queried."""
    corpus_config = resolve_active_corpus_config(db)
    db.add(
        Feedback(
            corpus=corpus_config.name,
            query=body.query,
            answer=body.answer,
            rating=body.rating,
        )
    )
    db.commit()
    return FeedbackResponse()
