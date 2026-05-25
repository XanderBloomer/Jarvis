"""Tests for the script generator service."""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from content_engine.models.scripts import Script, ScriptStatus
from content_engine.models.trends import HookAnalysis, Trend
from content_engine.services.llm.openai_client import OpenAIClient
from content_engine.services.script_generator import ScriptGenerator

SAMPLE_SCRIPT_RESPONSE = {
    "title": "The Mirror Watched Back",
    "hook": "I stopped looking in mirrors three days ago. Here's why.",
    "body": (
        "I stopped looking in mirrors three days ago. Here's why. "
        "It started with a flicker. Just a shadow in the corner of the bathroom mirror. "
        "I told myself it was nothing. But the next night, the shadow had moved closer. "
        "It had a shape now. Shoulders. A head. Standing right behind me. "
        "I spun around. Nothing there. But when I looked back at the mirror, "
        "it was still there. And it was smiling. "
        "I covered every mirror in my apartment. Taped newspapers over them. "
        "But this morning, I found the tape peeled back on one. "
        "And there were fingerprints on the glass. From the inside. "
        "The worst part? I just noticed something. "
        "My reflection in my phone screen? It's not moving when I do."
    ),
    "twist": "There were fingerprints on the glass. From the inside.",
    "ending": "My reflection in my phone screen? It's not moving when I do.",
    "word_count": 148,
    "tone_tags": ["dread", "paranoia", "body_horror", "psychological"],
    "visual_cues": [
        "Dark bathroom, flickering light, mirror with shadowy figure",
        "Close-up of mirror with shape forming behind reflection",
        "Hands taping newspaper over mirrors frantically",
        "Peeled tape with fingerprints visible on glass surface",
        "Phone screen showing still reflection while hand moves",
    ],
}

SAMPLE_HOOK_VARIANTS_RESPONSE = {
    "hooks": [
        {"content": "What would you do if your reflection stopped copying you?", "style": "question"},
        {"content": "Three days ago, something in my mirror moved on its own.", "style": "statement"},
        {"content": "The fingerprints on my mirror are on the wrong side.", "style": "revelation"},
    ]
}

SAMPLE_ENDING_VARIANTS_RESPONSE = {
    "endings": [
        {"content": "I just realized — when did my reflection start blinking before I do?", "style": "loop_trigger"},
        {"content": "If you're watching this on your phone, don't look at the black edges of your screen.", "style": "comment_bait"},
        {"content": "The covered mirrors are fine. But I can't cover every reflective surface in my life.", "style": "cliffhanger"},
    ]
}


def make_hook_analysis() -> HookAnalysis:
    """Create a mock HookAnalysis for testing."""
    analysis = HookAnalysis(
        id=uuid.uuid4(),
        trend_id=uuid.uuid4(),
        hook_type="fear_curiosity",
        emotional_tone="dread",
        avg_sentence_length=8,
        suggested_twist_position=0.7,
        cta_style="implicit",
        raw_analysis={
            "hook_text": "Something in my mirror moved on its own",
            "tension_arc": "slow reveal with escalating details",
            "retention_elements": ["mirror entity", "escalating danger"],
            "virality_score": 8,
        },
        quality_score=8.5,
    )
    return analysis


def make_trend() -> Trend:
    """Create a mock Trend for testing."""
    return Trend(
        id=uuid.uuid4(),
        source="reddit",
        source_url="https://www.reddit.com/r/nosleep/comments/test/",
        title="Something is watching me from the mirror every night",
        description="It started three weeks ago when I noticed a shadow...",
        keywords=["mirror", "watching", "shadow", "r/nosleep"],
        category="r/nosleep",
        engagement_score=1200.0,
        trending_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


@pytest.fixture
def mock_llm() -> MagicMock:
    """Create a mock OpenAI client that returns script data."""
    mock = MagicMock(spec=OpenAIClient)
    mock._model = "gpt-4o"
    mock.complete_json.side_effect = [
        SAMPLE_SCRIPT_RESPONSE.copy(),
        SAMPLE_HOOK_VARIANTS_RESPONSE.copy(),
        SAMPLE_ENDING_VARIANTS_RESPONSE.copy(),
    ]
    return mock


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock database session."""
    session = MagicMock()
    session.add = MagicMock()
    session.flush = MagicMock()
    session.get = MagicMock(return_value=make_trend())
    return session


class TestScriptGenerator:
    """Tests for the ScriptGenerator service."""

    def test_generate_from_hook_creates_script(
        self, mock_session: MagicMock, mock_llm: MagicMock
    ) -> None:
        """generate_from_hook returns a populated Script."""
        generator = ScriptGenerator(session=mock_session, llm_client=mock_llm)
        analysis = make_hook_analysis()
        trend = make_trend()

        script = generator.generate_from_hook(analysis, trend=trend)

        assert isinstance(script, Script)
        assert script.title == "The Mirror Watched Back"
        assert script.target_duration == "60s"
        assert script.hook == "I stopped looking in mirrors three days ago. Here's why."
        assert "fingerprints" in script.twist
        assert script.niche == "creepy_horror"
        assert script.status == ScriptStatus.DRAFT.value
        mock_session.add.assert_called()

    def test_generate_from_hook_stores_generation_params(
        self, mock_session: MagicMock, mock_llm: MagicMock
    ) -> None:
        """Script stores metadata about how it was generated."""
        generator = ScriptGenerator(session=mock_session, llm_client=mock_llm)
        analysis = make_hook_analysis()

        script = generator.generate_from_hook(analysis, trend=make_trend())

        assert script.generation_params is not None
        assert "tone_tags" in script.generation_params
        assert "visual_cues" in script.generation_params
        assert script.model_used == "gpt-4o"

    def test_generate_from_hook_with_variants(
        self, mock_session: MagicMock, mock_llm: MagicMock
    ) -> None:
        """generate_from_hook calls LLM 3 times (script + hook variants + ending variants)."""
        generator = ScriptGenerator(session=mock_session, llm_client=mock_llm)
        analysis = make_hook_analysis()

        generator.generate_from_hook(analysis, trend=make_trend(), generate_variants=True)

        # 3 calls: main script, hook variants, ending variants
        assert mock_llm.complete_json.call_count == 3

    def test_generate_from_hook_without_variants(
        self, mock_session: MagicMock, mock_llm: MagicMock
    ) -> None:
        """Without variants, only 1 LLM call is made."""
        mock_llm.complete_json.side_effect = [SAMPLE_SCRIPT_RESPONSE.copy()]
        generator = ScriptGenerator(session=mock_session, llm_client=mock_llm)
        analysis = make_hook_analysis()

        generator.generate_from_hook(analysis, trend=make_trend(), generate_variants=False)

        assert mock_llm.complete_json.call_count == 1

    def test_generate_from_prompt_creates_script(
        self, mock_session: MagicMock, mock_llm: MagicMock
    ) -> None:
        """generate_from_prompt works without a hook analysis."""
        generator = ScriptGenerator(session=mock_session, llm_client=mock_llm)

        script = generator.generate_from_prompt(
            topic="A phone that shows your death date",
            hook_type="mystery_gap",
            emotional_tone="dread",
        )

        assert isinstance(script, Script)
        assert script.title == "The Mirror Watched Back"
        assert script.target_duration == "60s"
        assert script.trend_id is None  # No associated trend

    def test_generate_batch_processes_multiple(
        self, mock_session: MagicMock, mock_llm: MagicMock
    ) -> None:
        """generate_batch creates scripts for each analysis."""
        # Need enough responses for 2 scripts with variants
        mock_llm.complete_json.side_effect = [
            SAMPLE_SCRIPT_RESPONSE.copy(),
            SAMPLE_HOOK_VARIANTS_RESPONSE.copy(),
            SAMPLE_ENDING_VARIANTS_RESPONSE.copy(),
            SAMPLE_SCRIPT_RESPONSE.copy(),
            SAMPLE_HOOK_VARIANTS_RESPONSE.copy(),
            SAMPLE_ENDING_VARIANTS_RESPONSE.copy(),
        ]

        generator = ScriptGenerator(session=mock_session, llm_client=mock_llm)
        analyses = [make_hook_analysis() for _ in range(2)]

        scripts = generator.generate_batch(analyses)

        assert len(scripts) == 2

    def test_generate_batch_continues_on_error(
        self, mock_session: MagicMock, mock_llm: MagicMock
    ) -> None:
        """Batch continues if one generation fails."""
        mock_llm.complete_json.side_effect = [
            SAMPLE_SCRIPT_RESPONSE.copy(),
            SAMPLE_HOOK_VARIANTS_RESPONSE.copy(),
            SAMPLE_ENDING_VARIANTS_RESPONSE.copy(),
            ValueError("API error"),  # Second script fails
            SAMPLE_SCRIPT_RESPONSE.copy(),
            SAMPLE_HOOK_VARIANTS_RESPONSE.copy(),
            SAMPLE_ENDING_VARIANTS_RESPONSE.copy(),
        ]

        generator = ScriptGenerator(session=mock_session, llm_client=mock_llm)
        analyses = [make_hook_analysis() for _ in range(3)]

        scripts = generator.generate_batch(analyses)

        # 2 succeeded, 1 failed
        assert len(scripts) == 2

    def test_generate_uses_high_temperature(
        self, mock_session: MagicMock, mock_llm: MagicMock
    ) -> None:
        """Script generation uses higher temperature for creativity."""
        mock_llm.complete_json.side_effect = [SAMPLE_SCRIPT_RESPONSE.copy()]
        generator = ScriptGenerator(session=mock_session, llm_client=mock_llm)
        analysis = make_hook_analysis()

        generator.generate_from_hook(analysis, trend=make_trend(), generate_variants=False)

        call_kwargs = mock_llm.complete_json.call_args[1]
        assert call_kwargs["temperature"] == 0.8


class TestScriptQuality:
    """Tests for script quality estimation."""

    def test_perfect_word_count_scores_high(self) -> None:
        """Script with 140-160 words gets high quality."""
        result = SAMPLE_SCRIPT_RESPONSE.copy()
        result["word_count"] = 150
        score = ScriptGenerator._estimate_quality(result)
        assert score >= 8.0

    def test_out_of_range_word_count(self) -> None:
        """Script far from target word count scores lower."""
        result = SAMPLE_SCRIPT_RESPONSE.copy()
        result["word_count"] = 80
        score = ScriptGenerator._estimate_quality(result)
        assert score < 8.0

    def test_missing_sections_reduce_quality(self) -> None:
        """Missing title/hook/body/twist/ending reduces score."""
        result = {"word_count": 150, "title": "Test", "body": "content"}
        score = ScriptGenerator._estimate_quality(result)
        # Missing hook, twist, ending
        full_result = SAMPLE_SCRIPT_RESPONSE.copy()
        full_score = ScriptGenerator._estimate_quality(full_result)
        assert score < full_score

    def test_quality_capped_at_10(self) -> None:
        """Quality score never exceeds 10."""
        result = SAMPLE_SCRIPT_RESPONSE.copy()
        result["word_count"] = 150
        score = ScriptGenerator._estimate_quality(result)
        assert score <= 10.0
