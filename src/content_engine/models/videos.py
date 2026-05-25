"""Models for video assembly and assets."""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from content_engine.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from content_engine.models.analytics import VideoAnalytics


class VideoStatus(StrEnum):
    """Status of a video in the pipeline."""

    PENDING = "pending"
    GENERATING_VOICE = "generating_voice"
    GENERATING_VISUALS = "generating_visuals"
    ASSEMBLING = "assembling"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    REJECTED = "rejected"


class Video(Base, UUIDMixin, TimestampMixin):
    """A produced video ready for publishing."""

    __tablename__ = "videos"

    # Source script
    script_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scripts.id"), nullable=False
    )

    # Video metadata
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Technical details
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 1080x1920
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Pipeline status
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=VideoStatus.PENDING.value
    )

    # Publishing
    platform: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # tiktok, youtube, etc.
    platform_video_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    published_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    assets: Mapped[list[VideoAsset]] = relationship(back_populates="video")
    analytics: Mapped[list[VideoAnalytics]] = relationship(
        "VideoAnalytics", back_populates="video"
    )


class VideoAsset(Base, UUIDMixin, TimestampMixin):
    """Individual assets that compose a video (audio, images, subtitles)."""

    __tablename__ = "video_assets"

    # Foreign key
    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("videos.id"), nullable=False
    )

    # Asset info
    asset_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # voice, image, music, subtitle
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Timing
    start_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Generation metadata
    generation_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    video: Mapped[Video] = relationship(back_populates="assets")
