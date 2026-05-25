"""Models for video performance analytics and feedback loops."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from content_engine.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from content_engine.models.videos import Video


class VideoAnalytics(Base, UUIDMixin, TimestampMixin):
    """Performance metrics for a published video."""

    __tablename__ = "video_analytics"

    # Foreign key
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("videos.id"), nullable=False
    )

    # Core metrics
    views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    likes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comments: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    shares: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    saves: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Retention metrics
    avg_watch_duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    completion_rate: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0.0-1.0

    # Engagement ratios (computed)
    engagement_rate: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Platform
    platform: Mapped[str] = mapped_column(String(50), nullable=False)

    # Snapshot time (metrics change over time)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Raw platform response
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    video: Mapped[Video] = relationship(back_populates="analytics")
