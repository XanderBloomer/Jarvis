"""CLI command to generate voice narration from scripts."""

import logging
import sys
from pathlib import Path

from content_engine.config.database import get_session_factory
from content_engine.services.voice.voice_generator import VoiceGenerator


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for CLI usage."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def run_voice_generator(
    limit: int = 5,
    voice_profile: str = "narrator_deep",
    output_dir: str | None = None,
    dry_run: bool = False,
) -> None:
    """Generate narration audio for scripts.

    Args:
        limit: Number of scripts to process
        voice_profile: Voice profile to use (narrator_deep, narrator_eerie, narrator_whisper)
        output_dir: Override output directory
        dry_run: Show what would be generated without calling ElevenLabs
    """
    logger = logging.getLogger(__name__)

    session_factory = get_session_factory()
    session = session_factory()

    try:
        out_path = Path(output_dir) if output_dir else None
        generator = VoiceGenerator(
            session=session,
            output_dir=out_path,
            voice_profile=voice_profile,
        )

        # Find scripts needing audio
        scripts = generator.get_scripts_needing_audio(limit=limit)

        if not scripts:
            logger.info("No scripts need audio generation. Generate scripts first.")
            return

        logger.info(f"Found {len(scripts)} scripts needing audio")

        if dry_run:
            print(f"\n{'='*70}")
            print(f"{'TITLE':<45} {'WORDS':>5} {'~DURATION':>10}")
            print(f"{'='*70}")
            for script in scripts:
                title = script.title[:43]
                words = len(script.body.split())
                duration = words / 2.5
                print(f"{title:<45} {words:>5} {duration:>8.1f}s")
            print(f"{'='*70}")
            total_words = sum(len(s.body.split()) for s in scripts)
            total_duration = total_words / 2.5
            print(f"Total: {len(scripts)} scripts, ~{total_duration:.0f}s of audio")
            print(f"Voice: {voice_profile}")
            print("(Use without --dry-run to generate audio via ElevenLabs)")
            return

        # Generate audio
        logger.info(f"Generating audio with voice profile: {voice_profile}")
        assets = generator.generate_batch(scripts)
        session.commit()

        # Print summary
        print(f"\n{'='*70}")
        print(f"{'TITLE':<40} {'DURATION':>8} {'FILE':>20}")
        print(f"{'='*70}")
        for asset in assets:
            params = asset.generation_params or {}
            title = Path(asset.file_path).stem[:38]
            duration = params.get("estimated_duration_seconds", 0)
            filename = Path(asset.file_path).name[-18:]
            print(f"{title:<40} {duration:>6.1f}s {filename:>20}")
        print(f"{'='*70}")
        print(f"Generated {len(assets)} audio files")

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    """CLI entry point for voice generation."""
    setup_logging()

    args = sys.argv[1:]

    dry_run = "--dry-run" in args
    limit = 5
    voice_profile = "narrator_deep"
    output_dir: str | None = None

    for i, arg in enumerate(args):
        if arg == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])
        elif arg == "--voice" and i + 1 < len(args):
            voice_profile = args[i + 1]
        elif arg == "--output-dir" and i + 1 < len(args):
            output_dir = args[i + 1]

    run_voice_generator(
        limit=limit,
        voice_profile=voice_profile,
        output_dir=output_dir,
        dry_run=dry_run,
    )


if __name__ == "__main__":
    main()
