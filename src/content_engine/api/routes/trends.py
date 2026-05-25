"""API routes for trend management."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from content_engine.config.database import get_db
from content_engine.services.trend_service import TrendService

router = APIRouter(prefix="/trends", tags=["trends"])


class TrendResponse(BaseModel):
    """Response model for a single trend."""

    id: UUID
    source: str
    source_url: str | None
    title: str
    description: str | None
    keywords: list[str] | None
    category: str | None
    engagement_score: float | None
    trending_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class TrendListResponse(BaseModel):
    """Response model for a list of trends."""

    trends: list[TrendResponse]
    count: int


@router.get("", response_model=TrendListResponse)
def list_trends(
    limit: int = Query(default=50, ge=1, le=200),
    source: str | None = Query(default=None),
    min_engagement: float | None = Query(default=None),
    db: Session = Depends(get_db),
) -> TrendListResponse:
    """List recent trends with optional filters."""
    service = TrendService(db)
    trends = service.get_recent_trends(
        limit=limit,
        source=source,
        min_engagement=min_engagement,
    )
    return TrendListResponse(
        trends=[TrendResponse.model_validate(t) for t in trends],
        count=len(trends),
    )


@router.get("/top", response_model=TrendListResponse)
def top_trends(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> TrendListResponse:
    """Get top-performing trends from today."""
    service = TrendService(db)
    trends = service.get_top_trends(limit=limit)
    return TrendListResponse(
        trends=[TrendResponse.model_validate(t) for t in trends],
        count=len(trends),
    )
