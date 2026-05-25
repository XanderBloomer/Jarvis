"""Visual Generator — produces scene images from script visual cues."""

import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from content_engine.models.scripts import Script
from content_engine.models.videos import Video, VideoAsset, VideoStatus
from content_engine.services.visuals.leonardo_client import (
    IMAGE_STYLES,
    LeonardoClient,
)

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = Path("output/images")


class VisualGenerator:
    """Generates scene images from script visual cues using Leonardo AI."""

    def __init__(
        self,
        session: Session,
        leonardo_client: LeonardoClient | None = None,
        output_dir: Path | None = None,
        style: str = "horror_dark",
    ):
        self.session = session
        self.leonardo = leonardo_client or LeonardoClient()
        self.output_dir = output_dir or DEFAULT_OUTPUT_DIR
        self.image_style = IMAGE_STYLES.get(style, IMAGE_STYLES["horror_dark"])

    def generate_for_script(self, script: Script) -> list[VideoAsset]:
        """Generate images for all visual cues in a script.

        Reads visual_cues from script.generation_params and generates
        one image per cue.

        Args:
            script: The script with visual_cues in generation_params

        Returns:
            List of VideoAsset records (type='image') linked to the video
        """
        # Get visual cues from generation params
        params = script.generation_params or {}
        visual_cues = params.get("visual_cues", [])

        if not visual_cues:
            logger.warning(f"No visual cues found for script: {script.title}")
            return []

        # Get or create the video record
        video = self._get_video_for_script(script)
        if not video:
            logger.error(f"No video record found for script: {script.title}")
            return []

        # Calculate timing for each scene
        duration = video.duration_seconds or 60.0
        scene_duration = duration / len(visual_cues)

        # Output directory for this script's images
        script_dir = self.output_dir / str(script.id)

        logger.info(
            f"Generating {len(visual_cues)} images for: {script.title} "
            f"(style={self.image_style.name})"
        )

        assets: list[VideoAsset] = []

        for i, cue in enumerate(visual_cues):
            try:
                result = self.leonardo.generate_image(
                    prompt=cue,
                    style=self.image_style,
                    output_dir=script_dir,
                )

                # Create VideoAsset for this image
                asset = VideoAsset(
                    video_id=video.id,
                    asset_type="image",
                    file_path=str(result.local_path or result.image_url),
                    sequence_order=i + 1,  # 1-indexed (0 is voice)
                    start_time_seconds=i * scene_duration,
                    end_time_seconds=(i + 1) * scene_duration,
                    generation_params={
                        "prompt": cue,
                        "style": self.image_style.name,
                        "generation_id": result.generation_id,
                        "image_url": result.image_url,
                        "seed": result.seed,
                    },
                )
                self.session.add(asset)
                assets.append(asset)

                logger.info(f"  [{i + 1}/{len(visual_cues)}] Generated: {cue[:50]}")

            except Exception as e:
                logger.error(f"  [{i + 1}/{len(visual_cues)}] Failed: {cue[:50]} - {e}")
                continue

        if assets:
            # Update video status
            video.status = VideoStatus.ASSEMBLING.value
            self.session.flush()
            logger.info(f"Generated {len(assets)}/{len(visual_cues)} images for: {script.title}")

        return assets

    def generate_batch(self, scripts: list[Script]) -> dict[str, list[VideoAsset]]:
        """Generate images for multiple scripts.

        Args:
            scripts: List of scripts to generate visuals for

        Returns:
            Dict mapping script ID to list of generated assets
        """
        results: dict[str, list[VideoAsset]] = {}

        for i, script in enumerate(scripts, 1):
            try:
                assets = self.generate_for_script(script)
                results[str(script.id)] = assets
                logger.info(f"[{i}/{len(scripts)}] Done: {script.title[:40]}")
            except Exception as e:
                logger.error(f"[{i}/{len(scripts)}] Failed: {script.title[:40]} - {e}")
                results[str(script.id)] = []
                continue

        total_images = sum(len(a) for a in results.values())
        logger.info(f"Batch complete: {total_images} images for {len(scripts)} scripts")
        return results

    def get_scripts_needing_visuals(self, limit: int = 10) -> list[Script]:
        """Get scripts that have audio but no images yet."""
        # Scripts with voice assets but no image assets
        scripts_with_images = (
            select(Video.script_id)
            .join(VideoAsset, Video.id == VideoAsset.video_id)
            .where(VideoAsset.asset_type == "image")
            .distinct()
            .scalar_subquery()
        )

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
                Script.id.in_(scripts_with_audio),
                Script.id.notin_(scripts_with_images),
            )
            .order_by(Script.estimated_quality.desc())
            .limit(limit)
        )

        result = self.session.execute(stmt)
        return list(result.scalars().all())

    def _get_video_for_script(self, script: Script) -> Video | None:
        """Get the Video record associated with a script."""
        stmt = select(Video).where(Video.script_id == script.id)
        return self.session.execute(stmt).scalar_one_or_none()
