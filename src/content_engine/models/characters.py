"""Models for consistent AI characters and scenes."""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from content_engine.models.base import Base, TimestampMixin, UUIDMixin


class Character(Base, UUIDMixin, TimestampMixin):
    """A recurring AI-generated character for brand consistency."""

    __tablename__ = "characters"

    # Identity
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Visual generation prompts
    appearance_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    style_keywords: Mapped[list | None] = mapped_column(JSON, nullable=True)
    negative_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Reference images (file paths or URLs)
    reference_images: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Generation parameters for consistency
    generation_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Active status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    scenes: Mapped[list["CharacterScene"]] = relationship(back_populates="character")


class CharacterScene(Base, UUIDMixin, TimestampMixin):
    """A generated scene featuring a character."""

    __tablename__ = "character_scenes"

    # Foreign keys
    character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("characters.id"), nullable=False
    )

    # Scene description
    scene_description: Mapped[str] = mapped_column(Text, nullable=False)
    scene_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    mood: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Generated output
    image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_seed: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Quality
    quality_score: Mapped[float | None] = mapped_column(None, nullable=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    character: Mapped["Character"] = relationship(back_populates="scenes")
