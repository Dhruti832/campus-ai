"""Admin endpoints: authenticated corpus stats, active-corpus switching,
re-ingestion, and creating/removing corpora at runtime. Phase 2 stretch
feature — see build plan section 4.

Deliberately does NOT use ``from __future__ import annotations``, for the
same reason as routes/chat.py: FastAPI resolves Pydantic annotations at
runtime, which postponed evaluation can break.
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.admin_service import get_corpus_stats, list_available_corpora, set_active_corpus
from app.config import get_settings
from app.corpus_store import (
    DEFAULT_MAX_PAGES,
    InvalidCorpusNameError,
    build_corpus_config_from_url,
    delete_corpus_config,
    load_dynamic_corpus_config,
    save_corpus_config,
    update_corpus_config,
)
from app.db.session import get_db
from app.ingestion.ingest_service import ingest_corpus

router = APIRouter(prefix="/admin")


def require_admin(x_admin_key: str = Header(default="")) -> None:
    settings = get_settings()
    if not settings.admin_api_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid or missing admin key")


class SetActiveCorpusRequest(BaseModel):
    corpus: str


class IngestRequest(BaseModel):
    corpus: str


class IngestResponse(BaseModel):
    sources_ingested: int
    chunks_ingested: int


class CreateCorpusRequest(BaseModel):
    name: str
    website_url: str
    persona: str | None = None
    max_pages: int = Field(default=DEFAULT_MAX_PAGES, ge=1, le=2000)


class CreateCorpusResponse(BaseModel):
    name: str


class UpdateCorpusRequest(BaseModel):
    website_url: str | None = None
    persona: str | None = None
    max_pages: int | None = Field(default=None, ge=1, le=2000)


class UpdateCorpusResponse(BaseModel):
    name: str


class CorpusDetailResponse(BaseModel):
    name: str
    website_url: str
    persona: str
    max_pages: int


@router.get("/corpora", dependencies=[Depends(require_admin)])
def corpora(db: Session = Depends(get_db)) -> list[dict]:  # noqa: B008
    return get_corpus_stats(db)


@router.post(
    "/corpora", dependencies=[Depends(require_admin)], response_model=CreateCorpusResponse
)
def create_corpus(body: CreateCorpusRequest, db: Session = Depends(get_db)) -> CreateCorpusResponse:  # noqa: B008
    if body.name in list_available_corpora(db):
        raise HTTPException(status_code=400, detail=f"Corpus already exists: {body.name!r}")

    try:
        config = build_corpus_config_from_url(
            body.name, body.website_url, body.persona, body.max_pages
        )
    except (InvalidCorpusNameError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    save_corpus_config(db, config)
    return CreateCorpusResponse(name=config.name)


@router.get(
    "/corpora/{name}", dependencies=[Depends(require_admin)], response_model=CorpusDetailResponse
)
def corpus_detail(name: str, db: Session = Depends(get_db)) -> CorpusDetailResponse:  # noqa: B008
    """Only for admin-created (dynamic) corpora — built-in ones aren't
    editable this way, so there's nothing to pre-fill an edit form with."""
    config = load_dynamic_corpus_config(db, name)
    if config is None:
        raise HTTPException(
            status_code=404, detail=f"No such corpus (or it's a built-in one): {name!r}"
        )
    website_url = config.crawl.seed_urls[0] if config.crawl.seed_urls else ""
    return CorpusDetailResponse(
        name=config.name,
        website_url=website_url,
        persona=config.persona,
        max_pages=config.crawl.max_pages,
    )


@router.patch(
    "/corpora/{name}", dependencies=[Depends(require_admin)], response_model=UpdateCorpusResponse
)
def edit_corpus(
    name: str, body: UpdateCorpusRequest, db: Session = Depends(get_db)  # noqa: B008
) -> UpdateCorpusResponse:
    try:
        config = update_corpus_config(
            db,
            name,
            website_url=body.website_url,
            persona=body.persona,
            max_pages=body.max_pages,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if config is None:
        raise HTTPException(
            status_code=404, detail=f"No such corpus (or it's a built-in one): {name!r}"
        )
    return UpdateCorpusResponse(name=config.name)


@router.delete("/corpora/{name}", dependencies=[Depends(require_admin)])
def remove_corpus(name: str, db: Session = Depends(get_db)) -> dict:  # noqa: B008
    if not delete_corpus_config(db, name):
        raise HTTPException(
            status_code=404, detail=f"No such corpus (or it's a built-in one): {name!r}"
        )
    return {"deleted": name}


@router.post("/active-corpus", dependencies=[Depends(require_admin)])
def active_corpus(body: SetActiveCorpusRequest, db: Session = Depends(get_db)) -> dict:  # noqa: B008
    try:
        set_active_corpus(db, body.corpus)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"active_corpus": body.corpus}


@router.post("/ingest", dependencies=[Depends(require_admin)], response_model=IngestResponse)
def ingest(body: IngestRequest, db: Session = Depends(get_db)) -> IngestResponse:  # noqa: B008
    if body.corpus not in list_available_corpora(db):
        raise HTTPException(status_code=400, detail=f"Unknown corpus: {body.corpus!r}")
    result = ingest_corpus(body.corpus, db)
    return IngestResponse(
        sources_ingested=result.sources_ingested, chunks_ingested=result.chunks_ingested
    )
