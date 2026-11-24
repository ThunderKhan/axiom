"""Read-only reviewed source and competitor claim previews; no fake durable runs."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field, field_validator

from app.auth import VerifiedPrincipal, get_verified_principal
from app.feed_source import FeedItem
from app.public_source import SourceAccessBlocked, SourceAcquisitionFailed, SourceRecord
from app.source_registry import Purpose, ReviewedSource, ReviewedSourceRegistry, SourceRateLimited
from app.workspace_http import ApiFailure, ErrorDTO, StrictBody, get_workspace_store
from app.workspace_store import WorkspaceStore

ClaimKind = Literal["features", "pricing", "positioning"]


class SourcePreviewBody(StrictBody):
    url: str = Field(min_length=10, max_length=2048)


class FeedPreviewBody(SourcePreviewBody):
    query: str = Field(default="", max_length=120)
    limit: int = Field(default=10, ge=1, le=20)


class FeedPreviewDTO(BaseModel):
    workspace_id: UUID
    feed_url: str
    source_family: Literal["rss_atom"] = "rss_atom"
    origin: Literal["live"] = "live"
    retrieved_at: datetime
    feed_content_digest: str
    publisher: str
    policy_review_id: str
    items: tuple[FeedItem, ...]
    persisted: Literal[False] = False
    independent_fact_verification: Literal[False] = False
    query_method: Literal["literal_all_terms"] = "literal_all_terms"


class ClaimCandidate(StrictBody):
    kind: ClaimKind
    locator: str = Field(min_length=1, max_length=200)

    @field_validator("locator")
    @classmethod
    def bounded_phrase(cls, value: str) -> str:
        if not value.strip() or any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
            raise ValueError("Enter a single-line exact phrase from the source")
        return value.strip()


class CompetitorPreviewBody(SourcePreviewBody):
    name: str = Field(min_length=1, max_length=120)
    confirmed: Literal[True]
    candidates: list[ClaimCandidate] = Field(default_factory=list, max_length=8)

    @field_validator("name")
    @classmethod
    def bounded_name(cls, value: str) -> str:
        if not value.strip() or any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
            raise ValueError("Enter a nonempty competitor name")
        return value.strip()


class SourcePreviewDTO(BaseModel):
    workspace_id: UUID
    source_id: str
    source_url: str
    source_family: Literal["manual_url"] = "manual_url"
    title: str
    excerpt: str
    origin: Literal["live"] = "live"
    retrieved_at: datetime
    content_digest: str
    publisher: str
    policy_review_id: str
    published_at: None = None
    persisted: Literal[False] = False
    independent_fact_verification: Literal[False] = False


class CompetitorClaimDTO(BaseModel):
    kind: ClaimKind
    text: str
    locator: str
    source_id: str
    status: Literal["publisher_claim_observed"] = "publisher_claim_observed"


class CompetitorPreviewDTO(BaseModel):
    competitor_name: str
    source: SourcePreviewDTO
    claims: list[CompetitorClaimDTO]
    unknowns: list[ClaimKind]
    warnings: list[str]


def get_source_registry(request: Request) -> ReviewedSourceRegistry:
    registry = getattr(request.app.state, "source_registry", None)
    if not isinstance(registry, ReviewedSourceRegistry):
        raise ApiFailure("SOURCE_UNAVAILABLE", 503, "Source registry unavailable.")
    return registry


def _retrieve(
    registry: ReviewedSourceRegistry, url: str, purpose: Purpose
) -> tuple[ReviewedSource, SourceRecord]:
    try:
        return registry.preview(url, purpose)
    except SourceAccessBlocked as exc:
        raise ApiFailure("SOURCE_BLOCKED", 403, "Source not permitted for this operation.") from exc
    except SourceRateLimited as exc:
        raise ApiFailure("SOURCE_RATE_LIMITED", 429, "Source request limit reached.") from exc
    except SourceAcquisitionFailed as exc:
        raise ApiFailure("SOURCE_UNAVAILABLE", 502, "Source could not be retrieved.") from exc


def _dto(workspace_id: UUID, review: ReviewedSource, record: SourceRecord) -> SourcePreviewDTO:
    return SourcePreviewDTO(
        workspace_id=workspace_id,
        source_id=record.source_record_id,
        source_url=record.canonical_url,
        title=record.title,
        excerpt=record.excerpt,
        retrieved_at=record.retrieved_at,
        content_digest=record.content_digest,
        publisher=review.publisher,
        policy_review_id=review.review_id,
    )


Principal = Annotated[VerifiedPrincipal, Depends(get_verified_principal)]
Store = Annotated[WorkspaceStore, Depends(get_workspace_store)]
Registry = Annotated[ReviewedSourceRegistry, Depends(get_source_registry)]

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}",
    tags=["source-preview"],
    responses={
        401: {"model": ErrorDTO},
        403: {"model": ErrorDTO},
        404: {"model": ErrorDTO},
        409: {"model": ErrorDTO},
        422: {"model": ErrorDTO},
        429: {"model": ErrorDTO},
        502: {"model": ErrorDTO},
        503: {"model": ErrorDTO},
    },
)


@router.post("/research/public-url/preview", response_model=SourcePreviewDTO)
def preview_source(
    workspace_id: UUID,
    body: SourcePreviewBody,
    principal: Principal,
    store: Store,
    registry: Registry,
    response: Response,
) -> SourcePreviewDTO:
    # Independently authorize the owner before any outbound network effect.
    store.get_workspace(principal, workspace_id)
    review, record = _retrieve(registry, body.url, "research_preview")
    response.headers["Cache-Control"] = "no-store"
    return _dto(workspace_id, review, record)


@router.post("/competitors/preview", response_model=CompetitorPreviewDTO)
def preview_competitor(
    workspace_id: UUID,
    body: CompetitorPreviewBody,
    principal: Principal,
    store: Store,
    registry: Registry,
    response: Response,
) -> CompetitorPreviewDTO:
    store.get_workspace(principal, workspace_id)
    review, record = _retrieve(registry, body.url, "competitor_preview")
    source = _dto(workspace_id, review, record)
    claims: list[CompetitorClaimDTO] = []
    kinds: tuple[ClaimKind, ...] = ("features", "pricing", "positioning")
    seen: set[tuple[ClaimKind, str]] = set()
    for candidate in body.candidates:
        # A literal quote must actually appear in the retrieved, bounded text.
        # The founder supplies the category; this is not independent inference.
        key = (candidate.kind, candidate.locator)
        if key in seen or candidate.locator not in record.excerpt:
            continue
        seen.add(key)
        claims.append(
            CompetitorClaimDTO(
                kind=candidate.kind,
                text=candidate.locator,
                locator=candidate.locator,
                source_id=source.source_id,
            )
        )
    response.headers["Cache-Control"] = "no-store"
    return CompetitorPreviewDTO(
        competitor_name=body.name,
        source=source,
        claims=claims,
        unknowns=[kind for kind in kinds if not any(claim.kind == kind for claim in claims)],
        warnings=[
            "Founder-suggested categories and exact matched excerpts, not verified capabilities.",
            "Only the bounded visible excerpt was checked. Unmatched claims remain unknown.",
            "This preview is not a saved competitor report or a research run.",
        ],
    )


@router.post("/research/feed/preview", response_model=FeedPreviewDTO)
def preview_feed(
    workspace_id: UUID,
    body: FeedPreviewBody,
    principal: Principal,
    store: Store,
    registry: Registry,
    response: Response,
) -> FeedPreviewDTO:
    store.get_workspace(principal, workspace_id)
    try:
        review, document, items = registry.preview_feed(
            body.url, query=body.query, limit=body.limit
        )
    except SourceAccessBlocked as exc:
        raise ApiFailure("SOURCE_BLOCKED", 403, "Feed is not permitted.") from exc
    except SourceRateLimited as exc:
        raise ApiFailure("SOURCE_RATE_LIMITED", 429, "Source request limit reached.") from exc
    except SourceAcquisitionFailed as exc:
        raise ApiFailure("SOURCE_UNAVAILABLE", 502, "Feed could not be parsed.") from exc
    response.headers["Cache-Control"] = "no-store"
    return FeedPreviewDTO(
        workspace_id=workspace_id,
        feed_url=document.url,
        retrieved_at=document.retrieved_at,
        feed_content_digest=hashlib.sha256(document.body).hexdigest(),
        publisher=review.publisher,
        policy_review_id=review.review_id,
        items=items,
    )
