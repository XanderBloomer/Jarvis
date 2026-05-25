"""Script Generator — produces 60-second horror video scripts from hook analyses."""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from content_engine.models.scripts import Script, ScriptStatus, ScriptVariant
from content_engine.models.trends import HookAnalysis, Trend
from content_engine.services.llm.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

# ~150 words = 60 seconds at narration pace
TARGET_WORD_COUNT = 150
WORDS_PER_SECOND = 2.5

SCRIPT_SYSTEM_PROMPT = """\
You are an expert short-form horror screenwriter. You write scripts for 60-second narrated videos (TikTok/YouTube Shorts/Reels).

Your scripts are:
- Exactly 140-160 words (this is critical — narration pace is ~2.5 words/second)
- Written in short, punchy sentences (5-10 words each)
- Designed for a single narrator voice-over
- Structured with a clear hook, escalation, twist, and ending
- In second person ("you") or first person ("I") for maximum immersion
- Designed to make viewers watch again (loop trigger at the end)

The horror niche thrives on:
- Curiosity gaps (what happens next?)
- Escalating dread (each sentence worse than the last)
- Familiar settings made wrong (home, bed, mirror, phone)
- Implied horror (what you DON'T show is scarier)
- A twist that recontextualizes everything before it

NEVER use clichés like "it was just a dream" or "and then I woke up".
Always respond in JSON format."""

SCRIPT_GENERATION_PROMPT = """\
Generate a 60-second horror narration script.

Inspiration (from trending content):
- Topic: {topic}
- Hook style: {hook_type}
- Emotional tone: {emotional_tone}
- Tension arc: {tension_arc}
- Suggested twist at: {twist_position}% through

{additional_context}

Respond with a JSON object:
{{
    "title": "<catchy title for the video, max 60 chars>",
    "hook": "<opening 1-2 sentences that grab attention instantly, ~10 words>",
    "body": "<full narration script, 140-160 words total including hook. Structure: hook → setup → escalation → twist → ending>",
    "twist": "<the twist moment extracted as a standalone sentence>",
    "ending": "<final 1-2 sentences that create a loop trigger or comment bait>",
    "word_count": <actual word count of the body>,
    "tone_tags": ["<2-4 mood/tone tags like: dread, paranoia, cosmic_horror, body_horror, psychological>"],
    "visual_cues": ["<3-5 brief visual scene descriptions for image generation>"]
}}"""

VARIANT_HOOK_PROMPT = """\
Generate 3 alternative opening hooks for this horror script.

Original script:
{body}

Original hook: "{original_hook}"

Each hook must:
- Be 8-12 words
- Create immediate curiosity or dread
- Work as the first thing a viewer hears
- Be different in approach (question, statement, revelation)

Respond with JSON:
{{
    "hooks": [
        {{"content": "<hook 1>", "style": "<question/statement/revelation/warning>"}},
        {{"content": "<hook 2>", "style": "<question/statement/revelation/warning>"}},
        {{"content": "<hook 3>", "style": "<question/statement/revelation/warning>"}}
    ]
}}"""

VARIANT_ENDING_PROMPT = """\
Generate 3 alternative endings for this horror script.

Script (without ending):
{body_without_ending}

Original ending: "{original_ending}"

Each ending must:
- Be 15-25 words
- Either: recontextualize the story, create a loop, or bait comments
- Leave the viewer unsettled
- Make them want to watch again or comment

Respond with JSON:
{{
    "endings": [
        {{"content": "<ending 1>", "style": "<loop_trigger/cliffhanger/comment_bait/recontextualization>"}},
        {{"content": "<ending 2>", "style": "<loop_trigger/cliffhanger/comment_bait/recontextualization>"}},
        {{"content": "<ending 3>", "style": "<loop_trigger/cliffhanger/comment_bait/recontextualization>"}}
    ]
}}"""


class ScriptGenerator:
    """Generates 60-second horror video scripts from hook analyses."""

    def __init__(
        self,
        session: Session,
        llm_client: OpenAIClient | None = None,
    ):
        self.session = session
        self.llm = llm_client or OpenAIClient()

    def generate_from_hook(
        self,
        hook_analysis: HookAnalysis,
        trend: Trend | None = None,
        generate_variants: bool = True,
    ) -> Script:
        """Generate a script from a hook analysis.

        Args:
            hook_analysis: The analyzed hook to base the script on
            trend: Optional associated trend for additional context
            generate_variants: Whether to generate hook/ending variants

        Returns:
            The created Script record (with variants if requested)
        """
        raw = hook_analysis.raw_analysis or {}

        # Build context from the trend
        additional_context = ""
        if trend:
            if trend.description:
                additional_context = f"Source material summary:\n{trend.description[:500]}"
            additional_context += f"\nKeywords: {', '.join(trend.keywords or [])}"

        # Generate the main script
        user_prompt = SCRIPT_GENERATION_PROMPT.format(
            topic=trend.title if trend else raw.get("hook_text", "a creepy scenario"),
            hook_type=hook_analysis.hook_type,
            emotional_tone=hook_analysis.emotional_tone,
            tension_arc=raw.get("tension_arc", "escalating dread"),
            twist_position=int((hook_analysis.suggested_twist_position or 0.7) * 100),
            additional_context=additional_context,
        )

        logger.info(f"Generating script from hook: {hook_analysis.hook_type}/{hook_analysis.emotional_tone}")

        result = self.llm.complete_json(
            system_prompt=SCRIPT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.8,  # Higher creativity for scripts
            max_tokens=1500,
        )

        # Create the Script record
        script = Script(
            title=result.get("title", "Untitled Horror"),
            body=result.get("body", ""),
            target_duration="60s",
            hook=result.get("hook", ""),
            twist=result.get("twist"),
            ending=result.get("ending"),
            niche="creepy_horror",
            prompt_template="script_generation_v1",
            model_used=self.llm._model,
            generation_params={
                "hook_analysis_id": str(hook_analysis.id),
                "trend_id": str(trend.id) if trend else None,
                "tone_tags": result.get("tone_tags", []),
                "visual_cues": result.get("visual_cues", []),
                "word_count": result.get("word_count"),
            },
            estimated_quality=self._estimate_quality(result),
            status=ScriptStatus.DRAFT.value,
            trend_id=trend.id if trend else None,
        )

        self.session.add(script)
        self.session.flush()  # Get the script ID

        logger.info(f"Generated script: '{script.title}' ({result.get('word_count', '?')} words)")

        # Generate variants
        if generate_variants:
            self._generate_variants(script, result)

        return script

    def generate_from_prompt(
        self,
        topic: str,
        hook_type: str = "fear_curiosity",
        emotional_tone: str = "dread",
        generate_variants: bool = True,
    ) -> Script:
        """Generate a script directly from a topic (no hook analysis needed).

        Useful for generating scripts without pre-scraped trends.
        """
        user_prompt = SCRIPT_GENERATION_PROMPT.format(
            topic=topic,
            hook_type=hook_type,
            emotional_tone=emotional_tone,
            tension_arc="escalating dread with sudden revelation",
            twist_position=70,
            additional_context="",
        )

        logger.info(f"Generating script from topic: {topic[:50]}")

        result = self.llm.complete_json(
            system_prompt=SCRIPT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.8,
            max_tokens=1500,
        )

        script = Script(
            title=result.get("title", "Untitled Horror"),
            body=result.get("body", ""),
            target_duration="60s",
            hook=result.get("hook", ""),
            twist=result.get("twist"),
            ending=result.get("ending"),
            niche="creepy_horror",
            prompt_template="script_generation_v1",
            model_used=self.llm._model,
            generation_params={
                "topic": topic,
                "tone_tags": result.get("tone_tags", []),
                "visual_cues": result.get("visual_cues", []),
                "word_count": result.get("word_count"),
            },
            estimated_quality=self._estimate_quality(result),
            status=ScriptStatus.DRAFT.value,
        )

        self.session.add(script)
        self.session.flush()

        if generate_variants:
            self._generate_variants(script, result)

        return script

    def generate_batch(
        self,
        hook_analyses: list[HookAnalysis],
        generate_variants: bool = True,
    ) -> list[Script]:
        """Generate scripts from multiple hook analyses.

        Args:
            hook_analyses: List of analyzed hooks to generate from
            generate_variants: Whether to generate variants for each

        Returns:
            List of generated Script records
        """
        scripts: list[Script] = []

        for i, analysis in enumerate(hook_analyses, 1):
            try:
                # Load the associated trend
                trend = self.session.get(Trend, analysis.trend_id)
                script = self.generate_from_hook(
                    hook_analysis=analysis,
                    trend=trend,
                    generate_variants=generate_variants,
                )
                scripts.append(script)
                logger.info(f"[{i}/{len(hook_analyses)}] Generated: {script.title}")
            except Exception as e:
                logger.error(f"[{i}/{len(hook_analyses)}] Failed: {e}")
                continue

        if scripts:
            self.session.flush()
            logger.info(f"Batch complete: {len(scripts)} scripts generated")

        return scripts

    def get_scripts(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> list[Script]:
        """Get generated scripts with optional status filter."""
        stmt = select(Script).order_by(Script.created_at.desc())
        if status:
            stmt = stmt.where(Script.status == status)
        stmt = stmt.limit(limit)
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    def _generate_variants(self, script: Script, raw_result: dict[str, Any]) -> None:
        """Generate hook and ending variants for a script."""
        # Hook variants
        try:
            hook_result = self.llm.complete_json(
                system_prompt=SCRIPT_SYSTEM_PROMPT,
                user_prompt=VARIANT_HOOK_PROMPT.format(
                    body=script.body,
                    original_hook=script.hook,
                ),
                temperature=0.9,
                max_tokens=500,
            )

            for i, hook in enumerate(hook_result.get("hooks", [])):
                variant = ScriptVariant(
                    script_id=script.id,
                    variant_type="hook",
                    content=hook.get("content", ""),
                    test_group=chr(65 + i),  # A, B, C
                    word_count=len(hook.get("content", "").split()),
                )
                self.session.add(variant)

            logger.debug(f"Generated {len(hook_result.get('hooks', []))} hook variants")
        except Exception as e:
            logger.warning(f"Failed to generate hook variants: {e}")

        # Ending variants
        try:
            # Remove the ending from body for context
            body_without = script.body
            if script.ending and script.ending in script.body:
                body_without = script.body.replace(script.ending, "").strip()

            ending_result = self.llm.complete_json(
                system_prompt=SCRIPT_SYSTEM_PROMPT,
                user_prompt=VARIANT_ENDING_PROMPT.format(
                    body_without_ending=body_without,
                    original_ending=script.ending or "",
                ),
                temperature=0.9,
                max_tokens=500,
            )

            for i, ending in enumerate(ending_result.get("endings", [])):
                variant = ScriptVariant(
                    script_id=script.id,
                    variant_type="ending",
                    content=ending.get("content", ""),
                    test_group=chr(65 + i),  # A, B, C
                    word_count=len(ending.get("content", "").split()),
                )
                self.session.add(variant)

            logger.debug(f"Generated {len(ending_result.get('endings', []))} ending variants")
        except Exception as e:
            logger.warning(f"Failed to generate ending variants: {e}")

    @staticmethod
    def _estimate_quality(result: dict[str, Any]) -> float:
        """Estimate script quality from generation output.

        Factors:
        - Word count in target range (140-160)
        - Has all required sections
        - Has visual cues (needed for video)
        """
        score = 5.0  # Base score

        # Word count accuracy (0-3 points)
        word_count = result.get("word_count", 0)
        if 135 <= word_count <= 165:
            score += 3.0
        elif 120 <= word_count <= 180:
            score += 1.5
        elif word_count > 0:
            score += 0.5

        # Completeness (0-2 points)
        required = ["title", "hook", "body", "twist", "ending"]
        present = sum(1 for k in required if result.get(k))
        score += (present / len(required)) * 2.0

        return round(min(score, 10.0), 1)
