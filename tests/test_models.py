"""Tests for database models."""

from content_engine.models import (
    Base,
    Character,
    HookAnalysis,
    Script,
    ScriptVariant,
    Trend,
    Video,
    VideoAnalytics,
    VideoAsset,
)


def test_all_models_have_tablename() -> None:
    """All models should have a __tablename__ defined."""
    models = [
        Trend, HookAnalysis, Script, ScriptVariant,
        Character, Video, VideoAsset, VideoAnalytics,
    ]
    for model in models:
        assert hasattr(model, "__tablename__")
        assert model.__tablename__ is not None


def test_base_metadata_has_tables() -> None:
    """Base metadata should contain all expected tables."""
    expected_tables = {
        "trends",
        "hook_analyses",
        "scripts",
        "script_variants",
        "characters",
        "character_scenes",
        "videos",
        "video_assets",
        "video_analytics",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(
        actual_tables
    ), f"Missing tables: {expected_tables - actual_tables}"


def test_trend_model_fields() -> None:
    """Trend model should have expected columns."""
    columns = {c.name for c in Trend.__table__.columns}
    assert "source" in columns
    assert "title" in columns
    assert "keywords" in columns
    assert "engagement_score" in columns
    assert "created_at" in columns


def test_script_model_fields() -> None:
    """Script model should have expected columns."""
    columns = {c.name for c in Script.__table__.columns}
    assert "title" in columns
    assert "body" in columns
    assert "hook" in columns
    assert "target_duration" in columns
    assert "niche" in columns
    assert "status" in columns


def test_video_model_fields() -> None:
    """Video model should have expected columns."""
    columns = {c.name for c in Video.__table__.columns}
    assert "script_id" in columns
    assert "title" in columns
    assert "duration_seconds" in columns
    assert "status" in columns
    assert "platform" in columns


def test_analytics_model_fields() -> None:
    """VideoAnalytics model should have expected columns."""
    columns = {c.name for c in VideoAnalytics.__table__.columns}
    assert "video_id" in columns
    assert "views" in columns
    assert "likes" in columns
    assert "completion_rate" in columns
    assert "engagement_rate" in columns


def test_character_model_fields() -> None:
    """Character model should have expected columns."""
    columns = {c.name for c in Character.__table__.columns}
    assert "name" in columns
    assert "appearance_prompt" in columns
    assert "style_keywords" in columns
    assert "reference_images" in columns
    assert "is_active" in columns
