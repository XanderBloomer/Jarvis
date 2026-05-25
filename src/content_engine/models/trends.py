"""Models for trend data and hook analysis."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from content_engine.models.base import Base, TimestampMixin, UUIDMixin


class Trend(Base, UUIDMixin, TimestampMixin):
    """A trending topic, phrase, or theme collected from external sources."""

    __tablename__ = "trends"

    # Source information
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # reddit, google, tiktok, etc.
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Content
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords: Mapped[list | None] = mapped_column(JSON, nullable=True)  # ["keyword1", "keyword2"]

    # Metadata
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    engagement_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    trending_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    hook_analyses: Mapped[list["HookAnalysis"]] = relationship(back_populates="trend")


class HookAnalysis(Base, UUIDMixin, TimestampMixin):
    """LLM-extracted analysis of a trend's hook potential."""

    __tablename__ = "hook_analyses"

    # Foreign key
    trend_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trends.id"), nullable=False
    )

    # Hook structure
    hook_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # fear_curiosity, shock, etc.
    emotional_tone: Mapped[str] = mapped_column(String(100), nullable=False)
    avg_sentence_length: Mapped[int | None] = mapped_column(Integer, nullable=True)
    suggested_twist_position: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # 0.0-1.0
    cta_style: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # implicit, explicit, none

    # Full analysis output
    raw_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Quality score (for filtering)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    trend: Mapped["Trend"] = relationship(back_populates="hook_analyses")
