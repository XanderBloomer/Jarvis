"""API routes for voice generation."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from content_engine.config.database import get_db
from content_engine.services.voice.elevenlabs_client import VOICE_PROFILES
from content_engine.services.voice.voice_generator import VoiceGenerator

router = APIRouter(prefix="/voice", tags=["voice"])


class VoiceProfileResponse(BaseModel):
    """Response model for a voice profile."""

    name: str
    voice_id: str
    voice_name: str
    model_id: str
    stability: float
    similarity_boost: float
    style: float


class NeedsAudioResponse(BaseModel):
    """Response for scripts needing audio."""

    count: int
    script_ids: list[UUID]


@router.get("/profiles")
def list_voice_profiles() -> list[VoiceProfileResponse]:
    """List available voice profiles for narration."""
    profiles = []
    for name, config in VOICE_PROFILES.items():
        profiles.append(
            VoiceProfileResponse(
                name=name,
                voice_id=config.voice_id,
                voice_name=config.voice_name,
                model_id=config.model_id,
                stability=config.stability,
                similarity_boost=config.similarity_boost,
                style=config.style,
            )
        )
    return profiles


@router.get("/needs-audio", response_model=NeedsAudioResponse)
def scripts_needing_audio(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> NeedsAudioResponse:
    """Get scripts that need audio generation."""
    generator = VoiceGenerator(session=db)
    scripts = generator.get_scripts_needing_audio(limit=limit)
    return NeedsAudioResponse(
        count=len(scripts),
        script_ids=[s.id for s in scripts],
    )
