"""API routes for script management."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from content_engine.config.database import get_db
from content_engine.services.script_generator import ScriptGenerator

router = APIRouter(prefix="/scripts", tags=["scripts"])


class ScriptVariantResponse(BaseModel):
    """Response model for a script variant."""

    id: UUID
    variant_type: str
    content: str
    test_group: str | None
    word_count: int | None

    model_config = {"from_attributes": True}


class ScriptResponse(BaseModel):
    """Response model for a single script."""

    id: UUID
    title: str
    body: str
    target_duration: str
    hook: str
    twist: str | None
    ending: str | None
    niche: str
    status: str
    estimated_quality: float | None
    generation_params: dict[str, Any] | None
    created_at: datetime
    variants: list[ScriptVariantResponse] = []

    model_config = {"from_attributes": True}


class ScriptListResponse(BaseModel):
    """Response model for a list of scripts."""

    scripts: list[ScriptResponse]
    count: int


@router.get("", response_model=ScriptListResponse)
def list_scripts(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> ScriptListResponse:
    """List generated scripts with optional status filter."""
    generator = ScriptGenerator(session=db)
    scripts = generator.get_scripts(status=status, limit=limit)
    return ScriptListResponse(
        scripts=[ScriptResponse.model_validate(s) for s in scripts],
        count=len(scripts),
    )


@router.get("/{script_id}", response_model=ScriptResponse)
def get_script(
    script_id: UUID,
    db: Session = Depends(get_db),
) -> ScriptResponse:
    """Get a single script by ID."""
    from content_engine.models.scripts import Script

    script = db.get(Script, script_id)
    if not script:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Script not found")
    return ScriptResponse.model_validate(script)
