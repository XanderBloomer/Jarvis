"""Reddit scraper for collecting trending horror/creepy content."""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx

logger = logging.getLogger(__name__)

# Subreddits relevant to creepy/horror niche
DEFAULT_SUBREDDITS = [
    "nosleep",
    "TwoSentenceHorror",
    "creepy",
    "shortscarystories",
    "scarystories",
    "Horror_stories",
    "DarkTales",
    "LibraryofShadows",
]

# Reddit JSON API base
REDDIT_BASE_URL = "https://www.reddit.com"

# Be a good citizen
USER_AGENT = "ContentEngine/0.1.0 (research; trend-collection)"


@dataclass
class RedditPost:
    """A scraped Reddit post."""

    post_id: str
    subreddit: str
    title: str
    selftext: str | None
    score: int
    upvote_ratio: float
    num_comments: int
    permalink: str
    created_utc: datetime
    url: str
    flair: str | None = None
    keywords: list[str] = field(default_factory=list)

    @property
    def engagement_score(self) -> float:
        """Calculate a normalized engagement score.

        Combines upvotes, comments, and ratio into a single score.
        Higher is better.
        """
        # Weight: score matters most, comments signal engagement, ratio signals quality
        return (self.score * 0.5) + (self.num_comments * 2.0) + (self.upvote_ratio * 100)

    @property
    def source_url(self) -> str:
        """Full Reddit URL for this post."""
        return f"{REDDIT_BASE_URL}{self.permalink}"


class RedditScraper:
    """Scrapes trending posts from horror/creepy subreddits."""

    def __init__(
        self,
        subreddits: list[str] | None = None,
        client: httpx.AsyncClient | None = None,
    ):
        self.subreddits = subreddits or DEFAULT_SUBREDDITS
        self._client = client
        self._owns_client = client is None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={"User-Agent": USER_AGENT},
                timeout=30.0,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client if we own it."""
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def fetch_subreddit(
        self,
        subreddit: str,
        sort: str = "hot",
        limit: int = 25,
        time_filter: str = "day",
    ) -> list[RedditPost]:
        """Fetch posts from a subreddit.

        Args:
            subreddit: Subreddit name (without r/)
            sort: Sort method - hot, top, new, rising
            limit: Number of posts to fetch (max 100)
            time_filter: Time filter for 'top' sort - hour, day, week, month, year, all
        """
        client = await self._get_client()

        url = f"{REDDIT_BASE_URL}/r/{subreddit}/{sort}.json"
        params: dict[str, str | int] = {"limit": min(limit, 100)}
        if sort == "top":
            params["t"] = time_filter

        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching r/{subreddit}: {e.response.status_code}")
            return []
        except httpx.RequestError as e:
            logger.error(f"Request error fetching r/{subreddit}: {e}")
            return []

        data = response.json()
        posts = []

        for child in data.get("data", {}).get("children", []):
            post_data = child.get("data", {})
            if not post_data:
                continue

            # Skip pinned/stickied posts
            if post_data.get("stickied", False):
                continue

            post = RedditPost(
                post_id=post_data["id"],
                subreddit=subreddit,
                title=post_data.get("title", ""),
                selftext=post_data.get("selftext") or None,
                score=post_data.get("score", 0),
                upvote_ratio=post_data.get("upvote_ratio", 0.0),
                num_comments=post_data.get("num_comments", 0),
                permalink=post_data.get("permalink", ""),
                created_utc=datetime.fromtimestamp(
                    post_data.get("created_utc", 0), tz=UTC
                ),
                url=post_data.get("url", ""),
                flair=post_data.get("link_flair_text"),
            )
            posts.append(post)

        logger.info(f"Fetched {len(posts)} posts from r/{subreddit} ({sort})")
        return posts

    async def fetch_all(
        self,
        sort: str = "hot",
        limit: int = 25,
        time_filter: str = "day",
    ) -> list[RedditPost]:
        """Fetch posts from all configured subreddits.

        Returns posts sorted by engagement score (highest first).
        """
        all_posts: list[RedditPost] = []

        for subreddit in self.subreddits:
            posts = await self.fetch_subreddit(
                subreddit=subreddit,
                sort=sort,
                limit=limit,
                time_filter=time_filter,
            )
            all_posts.extend(posts)

        # Sort by engagement score
        all_posts.sort(key=lambda p: p.engagement_score, reverse=True)

        logger.info(
            f"Total: {len(all_posts)} posts from {len(self.subreddits)} subreddits"
        )
        return all_posts

    async def fetch_trending(self, limit_per_sub: int = 25) -> list[RedditPost]:
        """Fetch trending content using multiple strategies.

        Combines hot posts and top posts from today for better coverage.
        Deduplicates by post_id.
        """
        seen_ids: set[str] = set()
        combined: list[RedditPost] = []

        # Strategy 1: Hot posts (currently trending)
        hot_posts = await self.fetch_all(sort="hot", limit=limit_per_sub)
        for post in hot_posts:
            if post.post_id not in seen_ids:
                seen_ids.add(post.post_id)
                combined.append(post)

        # Strategy 2: Top posts today (proven performers)
        top_posts = await self.fetch_all(
            sort="top", limit=limit_per_sub, time_filter="day"
        )
        for post in top_posts:
            if post.post_id not in seen_ids:
                seen_ids.add(post.post_id)
                combined.append(post)

        # Re-sort combined results
        combined.sort(key=lambda p: p.engagement_score, reverse=True)

        logger.info(f"Trending: {len(combined)} unique posts collected")
        return combined
