"""CLI command to generate scripts from analyzed hooks or topics."""

import logging
import sys

from content_engine.config.database import get_session_factory
from content_engine.services.hook_analyzer import HookAnalyzer
from content_engine.services.script_generator import ScriptGenerator


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for CLI usage."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def run_generator(
    limit: int = 5,
    topic: str | None = None,
    no_variants: bool = False,
) -> None:
    """Generate scripts from top hook analyses or a direct topic.

    Args:
        limit: Number of scripts to generate from hooks
        topic: Direct topic to generate from (skips hook lookup)
        no_variants: Skip generating hook/ending variants
    """
    logger = logging.getLogger(__name__)

    session_factory = get_session_factory()
    session = session_factory()

    try:
        generator = ScriptGenerator(session=session)

        if topic:
            # Generate from a direct topic
            logger.info(f"Generating script from topic: {topic}")
            script = generator.generate_from_prompt(
                topic=topic,
                generate_variants=not no_variants,
            )
            session.commit()

            print(f"\n{'='*70}")
            print(f"TITLE: {script.title}")
            print(f"{'='*70}")
            print(f"\nHOOK: {script.hook}")
            print(f"\nFULL SCRIPT:\n{script.body}")
            print(f"\nTWIST: {script.twist}")
            print(f"\nENDING: {script.ending}")
            print(f"\nWord count: {len(script.body.split())}")
            print(f"Quality: {script.estimated_quality}/10")

            if script.variants:
                print(f"\n{'─'*70}")
                print("VARIANTS:")
                for v in script.variants:
                    print(f"  [{v.variant_type}/{v.test_group}] {v.content}")

            print(f"{'='*70}")
            return

        # Generate from top hook analyses
        hook_analyzer = HookAnalyzer(session=session)
        top_hooks = hook_analyzer.get_top_hooks(limit=limit)

        if not top_hooks:
            logger.info("No analyzed hooks found. Run the analyzer first.")
            return

        logger.info(f"Generating {len(top_hooks)} scripts from top hooks...")
        scripts = generator.generate_batch(
            hook_analyses=top_hooks,
            generate_variants=not no_variants,
        )
        session.commit()

        # Print summary
        print(f"\n{'='*70}")
        print(f"{'TITLE':<40} {'WORDS':>5} {'QUALITY':>7}")
        print(f"{'='*70}")
        for script in scripts:
            title = script.title[:38]
            words = len(script.body.split())
            print(f"{title:<40} {words:>5} {script.estimated_quality:>7.1f}")
        print(f"{'='*70}")
        print(f"Generated {len(scripts)} scripts")

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    """CLI entry point for the script generator."""
    setup_logging()

    args = sys.argv[1:]

    topic: str | None = None
    limit = 5
    no_variants = "--no-variants" in args

    for i, arg in enumerate(args):
        if arg == "--topic" and i + 1 < len(args):
            topic = args[i + 1]
        elif arg == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])

    run_generator(limit=limit, topic=topic, no_variants=no_variants)


if __name__ == "__main__":
    main()
