"""Service for managing trends — scraping, storing, and querying."""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from content_engine.models.trends import Trend
from content_engine.services.scrapers.reddit import RedditPost

logger = logging.getLogger(__name__)


def extract_keywords(post: RedditPost) -> list[str]:
    """Extract keywords from a Reddit post title and text.

    Simple keyword extraction based on title words.
    Will be enhanced with LLM analysis in PR 3 (Hook Analyzer).
    """
    # Split title into words, filter short/common words
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
        "to", "for", "of", "and", "or", "but", "not", "with", "from",
        "by", "it", "its", "this", "that", "my", "your", "his", "her",
        "i", "me", "we", "you", "they", "he", "she", "what", "when",
        "where", "how", "why", "who", "which", "if", "then", "so",
        "just", "like", "about", "been", "had", "has", "have", "do",
        "did", "does", "will", "would", "could", "should", "can",
        "all", "each", "every", "no", "any", "some", "more", "most",
        "other", "than", "too", "very", "much", "many", "one", "two",
    }

    words = post.title.lower().split()
    keywords = [
        word.strip(".,!?;:'\"()[]{}") for word in words
        if len(word) > 3 and word.lower().strip(".,!?;:'\"()[]{}") not in stop_words
    ]

    # Add subreddit as a keyword
    keywords.append(f"r/{post.subreddit}")

    # Add flair if present
    if post.flair:
        keywords.append(post.flair.lower())

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_keywords: list[str] = []
    for kw in keywords:
        if kw and kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)

    return unique_keywords[:15]  # Cap at 15 keywords


def reddit_post_to_trend(post: RedditPost) -> Trend:
    """Convert a RedditPost to a Trend database model."""
    return Trend(
        source="reddit",
        source_url=post.source_url,
        title=post.title,
        description=post.selftext[:2000] if post.selftext else None,
        keywords=extract_keywords(post),
        category=f"r/{post.subreddit}",
        engagement_score=post.engagement_score,
        trending_at=post.created_utc,
    )


class TrendService:
    """Manages trend collection and storage."""

    def __init__(self, session: Session):
        self.session = session

    def trend_exists(self, source_url: str) -> bool:
        """Check if a trend with this source URL already exists."""
        stmt = select(Trend).where(Trend.source_url == source_url)
        return self.session.execute(stmt).scalar_one_or_none() is not None

    def store_trends(self, posts: list[RedditPost]) -> list[Trend]:
        """Store Reddit posts as trends, skipping duplicates.

        Returns the list of newly created Trend objects.
        """
        new_trends: list[Trend] = []

        for post in posts:
            source_url = post.source_url
            if self.trend_exists(source_url):
                logger.debug(f"Skipping duplicate: {post.title[:50]}")
                continue

            trend = reddit_post_to_trend(post)
            self.session.add(trend)
            new_trends.append(trend)

        if new_trends:
            self.session.flush()
            skipped = len(posts) - len(new_trends)
            logger.info(f"Stored {len(new_trends)} new trends (skipped {skipped} duplicates)")

        return new_trends

    def get_recent_trends(
        self,
        limit: int = 50,
        source: str | None = None,
        min_engagement: float | None = None,
    ) -> list[Trend]:
        """Fetch recent trends from the database.

        Args:
            limit: Maximum number of trends to return
            source: Filter by source (e.g., "reddit")
            min_engagement: Minimum engagement score filter
        """
        stmt = select(Trend).order_by(Trend.created_at.desc())

        if source:
            stmt = stmt.where(Trend.source == source)

        if min_engagement is not None:
            stmt = stmt.where(Trend.engagement_score >= min_engagement)

        stmt = stmt.limit(limit)
        result = self.session.execute(stmt)
        return list(result.scalars().all())

    def get_top_trends(
        self,
        limit: int = 20,
        hours_back: int = 24,
    ) -> list[Trend]:
        """Get top-performing trends from the last N hours."""
        cutoff = datetime.now(tz=UTC).replace(
            hour=0, minute=0, second=0
        )
        # Simple: just filter by engagement and recency
        stmt = (
            select(Trend)
            .where(Trend.created_at >= cutoff)
            .order_by(Trend.engagement_score.desc())
            .limit(limit)
        )
        result = self.session.execute(stmt)
        return list(result.scalars().all())
