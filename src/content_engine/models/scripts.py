"""Models for generated scripts and their variants."""

import uuid
from enum import StrEnum

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from content_engine.models.base import Base, TimestampMixin, UUIDMixin


class ScriptDuration(StrEnum):
    """Target duration for a script."""

    SHORT = "30s"
    MEDIUM = "45s"
    LONG = "60s"


class ScriptStatus(StrEnum):
    """Status of a script in the pipeline."""

    DRAFT = "draft"
    APPROVED = "approved"
    IN_PRODUCTION = "in_production"
    COMPLETED = "completed"
    REJECTED = "rejected"


class Script(Base, UUIDMixin, TimestampMixin):
    """A generated script for a short-form video."""

    __tablename__ = "scripts"

    # Content
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    target_duration: Mapped[str] = mapped_column(String(10), nullable=False)  # 30s, 45s, 60s

    # Structure metadata
    hook: Mapped[str] = mapped_column(Text, nullable=False)
    twist: Mapped[str | None] = mapped_column(Text, nullable=True)
    ending: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Generation context
    niche: Mapped[str] = mapped_column(String(100), nullable=False, default="creepy_horror")
    prompt_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    generation_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Scoring
    estimated_quality: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ScriptStatus.DRAFT.value
    )

    # Source trend (optional)
    trend_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trends.id"), nullable=True
    )

    # Relationships
    variants: Mapped[list["ScriptVariant"]] = relationship(back_populates="script")


class ScriptVariant(Base, UUIDMixin, TimestampMixin):
    """A variant of a script (different hook, ending, or title)."""

    __tablename__ = "script_variants"

    # Foreign key
    script_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scripts.id"), nullable=False
    )

    # What's different
    variant_type: Mapped[str] = mapped_column(String(50), nullable=False)  # hook, ending, title
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # A/B testing
    test_group: Mapped[str | None] = mapped_column(String(10), nullable=True)  # A, B, C...
    performance_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Word count for duration estimation
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    script: Mapped["Script"] = relationship(back_populates="variants")
