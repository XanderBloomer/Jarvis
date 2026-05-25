"""Hook Analyzer — LLM-powered analysis of trend content for hook potential."""

import logging
from typing import Any

from sqlalchemy.orm import Session

from content_engine.models.trends import HookAnalysis, Trend
from content_engine.services.llm.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

HOOK_ANALYSIS_SYSTEM_PROMPT = """You are an expert content strategist specializing in short-form video (TikTok, YouTube Shorts, Instagram Reels).

Your job is to analyze content and extract the structural elements that make it engaging — particularly for the horror/creepy/suspense niche.

You analyze:
- Hook type (what grabs attention in the first 2 seconds)
- Emotional structure (how feelings escalate)
- Pacing (sentence length, rhythm)
- Twist/surprise patterns
- What makes the content retain viewers

Always respond in JSON format."""

HOOK_ANALYSIS_USER_PROMPT = """Analyze the following content for its viral potential as a short-form video script.

Title: {title}

Content:
{content}

Source: {source} (engagement score: {engagement_score:.0f})

Respond with a JSON object containing:
{{
    "hook_type": "<type of hook: fear_curiosity, shock_reveal, mystery_gap, relatable_dread, forbidden_knowledge, countdown, or other>",
    "emotional_tone": "<primary emotional tone: dread, curiosity, suspense, horror, unease, paranoia, or other>",
    "avg_sentence_length": <estimated average words per sentence as integer>,
    "suggested_twist_position": <where the twist should land as 0.0-1.0 fraction of total duration, e.g. 0.7 means 70% through>,
    "cta_style": "<call-to-action style: implicit (curiosity drives comments), explicit (asks a question), cliffhanger, or none>",
    "hook_text": "<a 1-2 sentence hook that could open a 30-60 second video based on this content>",
    "tension_arc": "<brief description of how tension builds: e.g. 'slow reveal with escalating details'>",
    "retention_elements": [<list of 2-4 specific elements that would keep viewers watching>],
    "virality_score": <1-10 rating of how viral this could be as a short video>,
    "adaptation_notes": "<brief notes on how to adapt this into a 30-60 second video>"
}}"""


class HookAnalyzer:
    """Analyzes trends using LLM to extract hook patterns and structures."""

    def __init__(
        self,
        session: Session,
        llm_client: OpenAIClient | None = None,
    ):
        self.session = session
        self.llm = llm_client or OpenAIClient()

    def analyze_trend(self, trend: Trend) -> HookAnalysis:
        """Analyze a single trend and create a HookAnalysis record.

        Args:
            trend: The Trend to analyze

        Returns:
            The created HookAnalysis record (already added to session)
        """
        content = trend.description or trend.title
        # Truncate very long content to save tokens
        if len(content) > 3000:
            content = content[:3000] + "..."

        user_prompt = HOOK_ANALYSIS_USER_PROMPT.format(
            title=trend.title,
            content=content,
            source=trend.category or trend.source,
            engagement_score=trend.engagement_score or 0,
        )

        logger.info(f"Analyzing trend: {trend.title[:60]}...")

        raw_analysis = self.llm.complete_json(
            system_prompt=HOOK_ANALYSIS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.4,  # Lower temp for more consistent analysis
            max_tokens=1000,
        )

        # Create HookAnalysis record
        hook_analysis = HookAnalysis(
            trend_id=trend.id,
            hook_type=raw_analysis.get("hook_type", "unknown"),
            emotional_tone=raw_analysis.get("emotional_tone", "unknown"),
            avg_sentence_length=raw_analysis.get("avg_sentence_length"),
            suggested_twist_position=raw_analysis.get("suggested_twist_position"),
            cta_style=raw_analysis.get("cta_style"),
            raw_analysis=raw_analysis,
            quality_score=self._compute_quality_score(raw_analysis),
        )

        self.session.add(hook_analysis)
        logger.info(
            f"Analysis complete: hook={hook_analysis.hook_type}, "
            f"tone={hook_analysis.emotional_tone}, "
            f"quality={hook_analysis.quality_score:.1f}"
        )

        return hook_analysis

    def analyze_batch(
        self,
        trends: list[Trend],
        skip_existing: bool = True,
    ) -> list[HookAnalysis]:
        """Analyze multiple trends in sequence.

        Args:
            trends: List of Trends to analyze
            skip_existing: Skip trends that already have a HookAnalysis

        Returns:
            List of newly created HookAnalysis records
        """
        results: list[HookAnalysis] = []

        for i, trend in enumerate(trends, 1):
            if skip_existing and trend.hook_analyses:
                logger.debug(f"Skipping already-analyzed: {trend.title[:50]}")
                continue

            try:
                analysis = self.analyze_trend(trend)
                results.append(analysis)
                logger.info(f"[{i}/{len(trends)}] Analyzed: {trend.title[:50]}")
            except Exception as e:
                logger.error(f"[{i}/{len(trends)}] Failed to analyze: {trend.title[:50]} - {e}")
                continue

        if results:
            self.session.flush()
            logger.info(f"Batch complete: {len(results)} trends analyzed")

        return results

    def get_top_hooks(self, limit: int = 20) -> list[HookAnalysis]:
        """Get the highest-quality hook analyses."""
        from sqlalchemy import select

        stmt = (
            select(HookAnalysis)
            .where(HookAnalysis.quality_score.isnot(None))
            .order_by(HookAnalysis.quality_score.desc())
            .limit(limit)
        )
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    def get_unanalyzed_trends(self, limit: int = 50) -> list[Trend]:
        """Get trends that haven't been analyzed yet."""
        from sqlalchemy import select

        # Trends with no associated hook_analyses
        analyzed_ids = (
            select(HookAnalysis.trend_id).distinct().scalar_subquery()
        )
        stmt = (
            select(Trend)
            .where(Trend.id.notin_(analyzed_ids))
            .order_by(Trend.engagement_score.desc())
            .limit(limit)
        )
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def _compute_quality_score(analysis: dict[str, Any]) -> float:
        """Compute a quality score from the raw analysis.

        Factors:
        - Virality score (from LLM, 1-10)
        - Completeness (how many fields were filled)
        - Whether key elements are present
        """
        score = 0.0

        # Virality score contributes most (0-5 points)
        virality = analysis.get("virality_score", 5)
        score += min(virality, 10) / 2.0

        # Completeness (0-3 points)
        expected_keys = [
            "hook_type", "emotional_tone", "hook_text",
            "tension_arc", "retention_elements", "adaptation_notes",
        ]
        present = sum(1 for k in expected_keys if analysis.get(k))
        score += (present / len(expected_keys)) * 3.0

        # Retention elements quality (0-2 points)
        retention = analysis.get("retention_elements", [])
        if isinstance(retention, list) and len(retention) >= 2:
            score += min(len(retention), 4) / 2.0

        return round(score, 1)
