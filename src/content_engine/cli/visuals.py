"""CLI command to generate scene images from scripts."""

import logging
import sys
from pathlib import Path

from content_engine.config.database import get_session_factory
from content_engine.services.visuals.visual_generator import VisualGenerator


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for CLI usage."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def run_visual_generator(
    limit: int = 3,
    style: str = "horror_dark",
    output_dir: str | None = None,
    dry_run: bool = False,
) -> None:
    """Generate scene images for scripts that have audio.

    Args:
        limit: Number of scripts to process
        style: Image style preset (horror_dark, horror_surreal, horror_found_footage)
        output_dir: Override output directory
        dry_run: Show what would be generated without calling Leonardo AI
    """
    logger = logging.getLogger(__name__)

    session_factory = get_session_factory()
    session = session_factory()

    try:
        out_path = Path(output_dir) if output_dir else None
        generator = VisualGenerator(
            session=session,
            output_dir=out_path,
            style=style,
        )

        # Find scripts needing visuals
        scripts = generator.get_scripts_needing_visuals(limit=limit)

        if not scripts:
            logger.info("No scripts need visual generation. Generate voice first.")
            return

        logger.info(f"Found {len(scripts)} scripts needing visuals")

        if dry_run:
            print(f"\n{'='*70}")
            for script in scripts:
                params = script.generation_params or {}
                cues = params.get("visual_cues", [])
                print(f"\n  {script.title}")
                print(f"  {'─'*60}")
                for j, cue in enumerate(cues, 1):
                    print(f"    Scene {j}: {cue}")
                print(f"    → {len(cues)} images to generate")
            print(f"\n{'='*70}")
            total_images = sum(
                len((s.generation_params or {}).get("visual_cues", []))
                for s in scripts
            )
            print(f"Total: {len(scripts)} scripts, {total_images} images")
            print(f"Style: {style}")
            print("(Use without --dry-run to generate via Leonardo AI)")
            return

        # Generate images
        logger.info(f"Generating images with style: {style}")
        results = generator.generate_batch(scripts)
        session.commit()

        # Print summary
        print(f"\n{'='*70}")
        print(f"{'SCRIPT':<40} {'IMAGES':>6}")
        print(f"{'='*70}")
        for script in scripts:
            title = script.title[:38]
            count = len(results.get(str(script.id), []))
            print(f"{title:<40} {count:>6}")
        print(f"{'='*70}")
        total = sum(len(a) for a in results.values())
        print(f"Generated {total} images total")

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    """CLI entry point for visual generation."""
    setup_logging()

    args = sys.argv[1:]

    dry_run = "--dry-run" in args
    limit = 3
    style = "horror_dark"
    output_dir: str | None = None

    for i, arg in enumerate(args):
        if arg == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])
        elif arg == "--style" and i + 1 < len(args):
            style = args[i + 1]
        elif arg == "--output-dir" and i + 1 < len(args):
            output_dir = args[i + 1]

    run_visual_generator(
        limit=limit,
        style=style,
        output_dir=output_dir,
        dry_run=dry_run,
    )


if __name__ == "__main__":
    main()
