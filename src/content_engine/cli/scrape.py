"""CLI command to run the Reddit trend scraper."""

import asyncio
import logging
import sys

from content_engine.config.database import get_session_factory
from content_engine.services.scrapers.reddit import RedditScraper
from content_engine.services.trend_service import TrendService


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for CLI usage."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


async def run_scraper(
    subreddits: list[str] | None = None,
    limit: int = 25,
    sort: str = "hot",
    dry_run: bool = False,
) -> None:
    """Run the Reddit scraper and store results.

    Args:
        subreddits: Override default subreddit list
        limit: Posts per subreddit
        sort: Sort method (hot, top, new, rising)
        dry_run: If True, fetch but don't store in DB
    """
    logger = logging.getLogger(__name__)

    scraper = RedditScraper(subreddits=subreddits)
    try:
        logger.info("Starting Reddit trend collection...")
        posts = await scraper.fetch_trending(limit_per_sub=limit)
        logger.info(f"Collected {len(posts)} posts")

        if dry_run:
            logger.info("DRY RUN — not storing to database")
            print(f"\n{'='*60}")
            print(f"{'TITLE':<50} {'SCORE':>6} {'ENGAGEMENT':>10}")
            print(f"{'='*60}")
            for post in posts[:30]:
                title = post.title[:48]
                print(f"{title:<50} {post.score:>6} {post.engagement_score:>10.0f}")
            print(f"{'='*60}")
            print(f"Total: {len(posts)} posts")
            return

        # Store to database
        session_factory = get_session_factory()
        session = session_factory()
        try:
            service = TrendService(session)
            new_trends = service.store_trends(posts)
            session.commit()
            logger.info(f"Done! Stored {len(new_trends)} new trends in database.")
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    finally:
        await scraper.close()


def main() -> None:
    """CLI entry point for the scraper."""
    setup_logging()

    # Simple arg parsing (no click/argparse dependency needed yet)
    args = sys.argv[1:]

    dry_run = "--dry-run" in args
    limit = 25

    for i, arg in enumerate(args):
        if arg == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])

    asyncio.run(run_scraper(limit=limit, dry_run=dry_run))


if __name__ == "__main__":
    main()
