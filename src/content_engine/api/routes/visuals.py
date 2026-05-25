"""API routes for visual generation."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from content_engine.config.database import get_db
from content_engine.services.visuals.leonardo_client import IMAGE_STYLES
from content_engine.services.visuals.visual_generator import VisualGenerator

router = APIRouter(prefix="/visuals", tags=["visuals"])


class ImageStyleResponse(BaseModel):
    """Response model for an image style preset."""

    name: str
    style_prompt: str
    negative_prompt: str
    width: int
    height: int


class NeedsVisualsResponse(BaseModel):
    """Response for scripts needing visual generation."""

    count: int
    script_ids: list[UUID]


@router.get("/styles")
def list_image_styles() -> list[ImageStyleResponse]:
    """List available image style presets."""
    return [
        ImageStyleResponse(
            name=name,
            style_prompt=style.style_prompt,
            negative_prompt=style.negative_prompt,
            width=style.width,
            height=style.height,
        )
        for name, style in IMAGE_STYLES.items()
    ]


@router.get("/needs-visuals", response_model=NeedsVisualsResponse)
def scripts_needing_visuals(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> NeedsVisualsResponse:
    """Get scripts that have audio but need visual generation."""
    generator = VisualGenerator(session=db)
    scripts = generator.get_scripts_needing_visuals(limit=limit)
    return NeedsVisualsResponse(
        count=len(scripts),
        script_ids=[s.id for s in scripts],
    )
