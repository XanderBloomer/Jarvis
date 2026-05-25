"""Voice Generator — converts scripts to narrated audio files."""

import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from content_engine.models.scripts import Script, ScriptStatus
from content_engine.models.videos import Video, VideoAsset, VideoStatus
from content_engine.services.voice.elevenlabs_client import (
    VOICE_PROFILES,
    ElevenLabsClient,
)

logger = logging.getLogger(__name__)

# Default output directory for generated audio
DEFAULT_OUTPUT_DIR = Path("output/audio")


class VoiceGenerator:
    """Generates narration audio from scripts using ElevenLabs."""

    def __init__(
        self,
        session: Session,
        elevenlabs_client: ElevenLabsClient | None = None,
        output_dir: Path | None = None,
        voice_profile: str = "narrator_deep",
    ):
        self.session = session
        self.tts = elevenlabs_client or ElevenLabsClient()
        self.output_dir = output_dir or DEFAULT_OUTPUT_DIR
        self.voice_config = VOICE_PROFILES.get(voice_profile, VOICE_PROFILES["narrator_deep"])

    def generate_for_script(self, script: Script) -> VideoAsset:
        """Generate narration audio for a script.

        Creates a Video record (if not exists) and a VideoAsset for the audio.

        Args:
            script: The script to narrate

        Returns:
            The created VideoAsset record pointing to the audio file
        """
        # Determine output path
        safe_title = "".join(c if c.isalnum() or c in "-_ " else "" for c in script.title)
        safe_title = safe_title.strip().replace(" ", "_")[:50]
        filename = f"{script.id}_{safe_title}.mp3"
        output_path = self.output_dir / filename

        logger.info(f"Generating audio for: {script.title}")

        # Generate audio
        audio_path = self.tts.generate_speech(
            text=script.body,
            output_path=output_path,
            config=self.voice_config,
        )

        # Estimate duration from word count (~2.5 words/sec)
        word_count = len(script.body.split())
        estimated_duration = word_count / 2.5

        # Get or create a Video record for this script
        video = self._get_or_create_video(script)

        # Create the audio asset
        asset = VideoAsset(
            video_id=video.id,
            asset_type="voice",
            file_path=str(audio_path),
            sequence_order=0,  # Audio is always first asset
            start_time_seconds=0.0,
            end_time_seconds=estimated_duration,
            generation_params={
                "voice_profile": self.voice_config.voice_name,
                "voice_id": self.voice_config.voice_id,
                "model_id": self.voice_config.model_id,
                "word_count": word_count,
                "estimated_duration_seconds": estimated_duration,
            },
        )

        self.session.add(asset)

        # Update video status
        video.status = VideoStatus.GENERATING_VISUALS.value
        video.duration_seconds = estimated_duration

        # Update script status
        script.status = ScriptStatus.IN_PRODUCTION.value

        self.session.flush()

        logger.info(
            f"Audio generated: {audio_path.name} "
            f"(~{estimated_duration:.1f}s, {word_count} words)"
        )

        return asset

    def generate_batch(
        self,
        scripts: list[Script],
    ) -> list[VideoAsset]:
        """Generate audio for multiple scripts.

        Args:
            scripts: List of scripts to generate audio for

        Returns:
            List of created VideoAsset records
        """
        assets: list[VideoAsset] = []

        for i, script in enumerate(scripts, 1):
            try:
                asset = self.generate_for_script(script)
                assets.append(asset)
                logger.info(f"[{i}/{len(scripts)}] Done: {script.title[:40]}")
            except Exception as e:
                logger.error(f"[{i}/{len(scripts)}] Failed: {script.title[:40]} - {e}")
                continue

        if assets:
            self.session.flush()
            logger.info(f"Batch complete: {len(assets)} audio files generated")

        return assets

    def get_scripts_needing_audio(self, limit: int = 20) -> list[Script]:
        """Get approved/draft scripts that don't have audio yet."""
        # Find scripts that have no associated video with voice assets
        scripts_with_audio = (
            select(Video.script_id)
            .join(VideoAsset, Video.id == VideoAsset.video_id)
            .where(VideoAsset.asset_type == "voice")
            .distinct()
            .scalar_subquery()
        )

        stmt = (
            select(Script)
            .where(
                Script.status.in_([ScriptStatus.DRAFT.value, ScriptStatus.APPROVED.value]),
                Script.id.notin_(scripts_with_audio),
            )
            .order_by(Script.estimated_quality.desc())
            .limit(limit)
        )

        result = self.session.execute(stmt)
        return list(result.scalars().all())

    def _get_or_create_video(self, script: Script) -> Video:
        """Get existing Video for a script or create a new one."""
        stmt = select(Video).where(Video.script_id == script.id)
        existing = self.session.execute(stmt).scalar_one_or_none()

        if existing:
            return existing

        video = Video(
            script_id=script.id,
            title=script.title,
            description=script.hook,
            tags=script.generation_params.get("tone_tags", []) if script.generation_params else [],
            resolution="1080x1920",  # Vertical video
            status=VideoStatus.GENERATING_VOICE.value,
        )
        self.session.add(video)
        self.session.flush()

        return video
