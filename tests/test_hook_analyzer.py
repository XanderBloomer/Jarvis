"""Tests for the hook analyzer service."""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from content_engine.models.trends import HookAnalysis, Trend
from content_engine.services.hook_analyzer import HookAnalyzer
from content_engine.services.llm.openai_client import OpenAIClient


def make_trend(
    title: str = "Something is watching me from the mirror",
    description: str = "It started three weeks ago when I noticed...",
    engagement_score: float = 500.0,
) -> Trend:
    """Create a mock Trend for testing."""
    trend = Trend(
        id=uuid.uuid4(),
        source="reddit",
        source_url="https://www.reddit.com/r/nosleep/comments/test/",
        title=title,
        description=description,
        keywords=["mirror", "watching", "r/nosleep"],
        category="r/nosleep",
        engagement_score=engagement_score,
        trending_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    # Mock the relationship
    trend.hook_analyses = []  # type: ignore[assignment]
    return trend


SAMPLE_ANALYSIS_RESPONSE = {
    "hook_type": "fear_curiosity",
    "emotional_tone": "dread",
    "avg_sentence_length": 8,
    "suggested_twist_position": 0.7,
    "cta_style": "implicit",
    "hook_text": "Every night at 3AM, my mirror shows someone standing behind me. Last night, it waved.",
    "tension_arc": "slow reveal with escalating details building to a shocking discovery",
    "retention_elements": [
        "mystery of the mirror entity",
        "escalating danger each night",
        "relatable setting (bedroom)",
        "implied threat to viewer",
    ],
    "virality_score": 8,
    "adaptation_notes": "Open with the mirror shot, use whispered narration, dark visuals with subtle movement",
}


@pytest.fixture
def mock_llm() -> MagicMock:
    """Create a mock OpenAI client."""
    mock = MagicMock(spec=OpenAIClient)
    mock.complete_json.return_value = SAMPLE_ANALYSIS_RESPONSE.copy()
    return mock


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock database session."""
    session = MagicMock()
    session.add = MagicMock()
    session.flush = MagicMock()
    session.execute = MagicMock()
    return session


class TestHookAnalyzer:
    """Tests for the HookAnalyzer service."""

    def test_analyze_trend_creates_hook_analysis(
        self, mock_session: MagicMock, mock_llm: MagicMock
    ) -> None:
        """analyze_trend returns a populated HookAnalysis."""
        analyzer = HookAnalyzer(session=mock_session, llm_client=mock_llm)
        trend = make_trend()

        result = analyzer.analyze_trend(trend)

        assert isinstance(result, HookAnalysis)
        assert result.trend_id == trend.id
        assert result.hook_type == "fear_curiosity"
        assert result.emotional_tone == "dread"
        assert result.avg_sentence_length == 8
        assert result.suggested_twist_position == 0.7
        assert result.cta_style == "implicit"
        assert result.raw_analysis == SAMPLE_ANALYSIS_RESPONSE
        mock_session.add.assert_called_once_with(result)

    def test_analyze_trend_calls_llm_with_correct_prompt(
        self, mock_session: MagicMock, mock_llm: MagicMock
    ) -> None:
        """analyze_trend passes trend content to the LLM."""
        analyzer = HookAnalyzer(session=mock_session, llm_client=mock_llm)
        trend = make_trend(
            title="The door opened by itself",
            description="I was home alone when...",
        )

        analyzer.analyze_trend(trend)

        # Verify LLM was called
        mock_llm.complete_json.assert_called_once()
        call_kwargs = mock_llm.complete_json.call_args[1]
        assert "system" in call_kwargs["system_prompt"].lower() or len(call_kwargs["system_prompt"]) > 0
        assert "The door opened by itself" in call_kwargs["user_prompt"]
        assert "I was home alone when..." in call_kwargs["user_prompt"]

    def test_analyze_trend_truncates_long_content(
        self, mock_session: MagicMock, mock_llm: MagicMock
    ) -> None:
        """Very long content is truncated before sending to LLM."""
        analyzer = HookAnalyzer(session=mock_session, llm_client=mock_llm)
        trend = make_trend(description="x" * 5000)

        analyzer.analyze_trend(trend)

        call_kwargs = mock_llm.complete_json.call_args[1]
        # Content should be truncated to 3000 + "..."
        assert len(call_kwargs["user_prompt"]) < 5000

    def test_analyze_trend_uses_title_when_no_description(
        self, mock_session: MagicMock, mock_llm: MagicMock
    ) -> None:
        """When description is None, title is used as content."""
        analyzer = HookAnalyzer(session=mock_session, llm_client=mock_llm)
        trend = make_trend(title="A very creepy title", description=None)
        trend.description = None

        analyzer.analyze_trend(trend)

        call_kwargs = mock_llm.complete_json.call_args[1]
        assert "A very creepy title" in call_kwargs["user_prompt"]

    def test_analyze_batch_processes_multiple(
        self, mock_session: MagicMock, mock_llm: MagicMock
    ) -> None:
        """analyze_batch processes all trends and returns results."""
        analyzer = HookAnalyzer(session=mock_session, llm_client=mock_llm)
        trends = [make_trend(title=f"Story {i}") for i in range(3)]

        results = analyzer.analyze_batch(trends)

        assert len(results) == 3
        assert mock_llm.complete_json.call_count == 3
        mock_session.flush.assert_called_once()

    def test_analyze_batch_skips_already_analyzed(
        self, mock_session: MagicMock, mock_llm: MagicMock
    ) -> None:
        """analyze_batch skips trends that already have analyses."""
        analyzer = HookAnalyzer(session=mock_session, llm_client=mock_llm)
        trends = [make_trend(title=f"Story {i}") for i in range(3)]
        # Mark first trend as already analyzed
        trends[0].hook_analyses = [MagicMock()]  # type: ignore[assignment]

        results = analyzer.analyze_batch(trends, skip_existing=True)

        assert len(results) == 2
        assert mock_llm.complete_json.call_count == 2

    def test_analyze_batch_continues_on_error(
        self, mock_session: MagicMock, mock_llm: MagicMock
    ) -> None:
        """analyze_batch continues processing if one trend fails."""
        # Second call raises an error
        mock_llm.complete_json.side_effect = [
            SAMPLE_ANALYSIS_RESPONSE.copy(),
            ValueError("API error"),
            SAMPLE_ANALYSIS_RESPONSE.copy(),
        ]

        analyzer = HookAnalyzer(session=mock_session, llm_client=mock_llm)
        trends = [make_trend(title=f"Story {i}") for i in range(3)]

        results = analyzer.analyze_batch(trends)

        # Should have 2 results (1 failed)
        assert len(results) == 2
        assert mock_llm.complete_json.call_count == 3


class TestQualityScore:
    """Tests for quality score computation."""

    def test_high_quality_analysis(self) -> None:
        """Complete analysis with high virality gets high score."""
        analysis = SAMPLE_ANALYSIS_RESPONSE.copy()
        score = HookAnalyzer._compute_quality_score(analysis)
        # virality=8 -> 4.0, completeness=6/6 -> 3.0, retention=4 -> 2.0 = 9.0
        assert score >= 8.0

    def test_low_quality_analysis(self) -> None:
        """Minimal analysis gets lower score."""
        analysis = {
            "hook_type": "unknown",
            "emotional_tone": "unknown",
            "virality_score": 3,
        }
        score = HookAnalyzer._compute_quality_score(analysis)
        assert score < 5.0

    def test_missing_virality_defaults_to_5(self) -> None:
        """Missing virality score defaults to 5."""
        analysis = {
            "hook_type": "fear_curiosity",
            "emotional_tone": "dread",
            "hook_text": "test",
            "tension_arc": "test",
            "retention_elements": ["a", "b"],
            "adaptation_notes": "test",
        }
        score = HookAnalyzer._compute_quality_score(analysis)
        # virality=5 -> 2.5, completeness=6/6 -> 3.0, retention=2 -> 1.0 = 6.5
        assert 5.0 <= score <= 7.0

    def test_empty_retention_elements(self) -> None:
        """Empty retention elements contribute 0 points."""
        analysis = {
            "hook_type": "fear_curiosity",
            "emotional_tone": "dread",
            "virality_score": 5,
            "retention_elements": [],
        }
        score = HookAnalyzer._compute_quality_score(analysis)
        # No retention bonus
        analysis_with_retention = {**analysis, "retention_elements": ["a", "b", "c"]}
        score_with = HookAnalyzer._compute_quality_score(analysis_with_retention)
        assert score_with > score
