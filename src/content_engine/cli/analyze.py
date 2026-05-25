"""CLI command to run the hook analyzer on collected trends."""

import logging
import sys

from content_engine.config.database import get_session_factory
from content_engine.services.hook_analyzer import HookAnalyzer


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for CLI usage."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def run_analyzer(limit: int = 10, dry_run: bool = False) -> None:
    """Run the hook analyzer on unanalyzed trends.

    Args:
        limit: Maximum number of trends to analyze
        dry_run: If True, show what would be analyzed but don't call OpenAI
    """
    logger = logging.getLogger(__name__)

    session_factory = get_session_factory()
    session = session_factory()

    try:
        analyzer = HookAnalyzer(session=session)

        # Get unanalyzed trends
        trends = analyzer.get_unanalyzed_trends(limit=limit)

        if not trends:
            logger.info("No unanalyzed trends found. Run the scraper first.")
            return

        logger.info(f"Found {len(trends)} unanalyzed trends")

        if dry_run:
            print(f"\n{'='*70}")
            print(f"{'TITLE':<55} {'ENGAGEMENT':>10}")
            print(f"{'='*70}")
            for trend in trends:
                title = trend.title[:53]
                score = trend.engagement_score or 0
                print(f"{title:<55} {score:>10.0f}")
            print(f"{'='*70}")
            print(f"Would analyze {len(trends)} trends (use without --dry-run to proceed)")
            return

        # Run analysis
        logger.info("Starting hook analysis (this calls OpenAI API)...")
        results = analyzer.analyze_batch(trends)
        session.commit()

        # Print results summary
        print(f"\n{'='*70}")
        print(f"{'TITLE':<35} {'HOOK TYPE':<18} {'TONE':<12} {'QUALITY':>7}")
        print(f"{'='*70}")
        for analysis in results:
            trend = next(t for t in trends if t.id == analysis.trend_id)
            title = trend.title[:33]
            print(
                f"{title:<35} {analysis.hook_type:<18} "
                f"{analysis.emotional_tone:<12} {analysis.quality_score:>7.1f}"
            )
        print(f"{'='*70}")
        print(f"Analyzed {len(results)} trends successfully")

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    """CLI entry point for the hook analyzer."""
    setup_logging()

    args = sys.argv[1:]

    dry_run = "--dry-run" in args
    limit = 10

    for i, arg in enumerate(args):
        if arg == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])

    run_analyzer(limit=limit, dry_run=dry_run)


if __name__ == "__main__":
    main()
