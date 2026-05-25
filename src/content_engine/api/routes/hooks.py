"""API routes for hook analysis."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from content_engine.config.database import get_db
from content_engine.services.hook_analyzer import HookAnalyzer

router = APIRouter(prefix="/hooks", tags=["hooks"])


class HookAnalysisResponse(BaseModel):
    """Response model for a single hook analysis."""

    id: UUID
    trend_id: UUID
    hook_type: str
    emotional_tone: str
    avg_sentence_length: int | None
    suggested_twist_position: float | None
    cta_style: str | None
    quality_score: float | None
    raw_analysis: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class HookListResponse(BaseModel):
    """Response model for a list of hook analyses."""

    hooks: list[HookAnalysisResponse]
    count: int


@router.get("/top", response_model=HookListResponse)
def top_hooks(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> HookListResponse:
    """Get top-quality hook analyses."""
    analyzer = HookAnalyzer(session=db)
    hooks = analyzer.get_top_hooks(limit=limit)
    return HookListResponse(
        hooks=[HookAnalysisResponse.model_validate(h) for h in hooks],
        count=len(hooks),
    )


@router.get("/unanalyzed-count")
def unanalyzed_count(
    db: Session = Depends(get_db),
) -> dict[str, int]:
    """Get count of trends that haven't been analyzed yet."""
    analyzer = HookAnalyzer(session=db)
    trends = analyzer.get_unanalyzed_trends(limit=1000)
    return {"unanalyzed_count": len(trends)}
