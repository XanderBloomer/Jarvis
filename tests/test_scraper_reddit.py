"""Tests for the Reddit scraper."""

from unittest.mock import AsyncMock

import httpx
import pytest

from content_engine.services.scrapers.reddit import (
    RedditPost,
    RedditScraper,
)


def make_reddit_response(posts: list[dict]) -> dict:
    """Create a mock Reddit JSON API response."""
    children = []
    for post in posts:
        children.append({
            "kind": "t3",
            "data": {
                "id": post.get("id", "abc123"),
                "subreddit": post.get("subreddit", "nosleep"),
                "title": post.get("title", "A creepy story"),
                "selftext": post.get("selftext", "This is the story content..."),
                "score": post.get("score", 500),
                "upvote_ratio": post.get("upvote_ratio", 0.95),
                "num_comments": post.get("num_comments", 42),
                "permalink": post.get(
                    "permalink", f"/r/nosleep/comments/{post.get('id', 'abc123')}/a_creepy_story/"
                ),
                "created_utc": post.get("created_utc", 1700000000),
                "url": post.get("url", "https://reddit.com/r/nosleep/comments/abc123/"),
                "link_flair_text": post.get("flair", None),
                "stickied": post.get("stickied", False),
            },
        })

    return {
        "kind": "Listing",
        "data": {
            "children": children,
            "after": "t3_nextpage",
            "before": None,
        },
    }


@pytest.fixture
def sample_posts() -> list[dict]:
    """Sample post data for mocking."""
    return [
        {
            "id": "post1",
            "subreddit": "nosleep",
            "title": "Something is watching me from the mirror every night",
            "selftext": "It started three weeks ago...",
            "score": 1200,
            "upvote_ratio": 0.97,
            "num_comments": 89,
            "created_utc": 1700000000,
            "flair": "Series",
        },
        {
            "id": "post2",
            "subreddit": "nosleep",
            "title": "My daughter's imaginary friend left footprints",
            "selftext": "We moved into this house last month...",
            "score": 850,
            "upvote_ratio": 0.94,
            "num_comments": 156,
            "created_utc": 1700001000,
            "flair": None,
        },
        {
            "id": "post3",
            "subreddit": "nosleep",
            "title": "The previous tenant left a list of rules",
            "selftext": "Rule 1: Never look under the bed after midnight.",
            "score": 2400,
            "upvote_ratio": 0.98,
            "num_comments": 203,
            "created_utc": 1700002000,
            "flair": "Series",
        },
        {
            "id": "stickied_post",
            "subreddit": "nosleep",
            "title": "Monthly contest thread",
            "selftext": "Submit your stories here",
            "score": 50,
            "upvote_ratio": 0.90,
            "num_comments": 10,
            "created_utc": 1699900000,
            "stickied": True,
        },
    ]


@pytest.fixture
def mock_client(sample_posts: list[dict]) -> httpx.AsyncClient:
    """Create a mock httpx client that returns sample Reddit data."""
    response_data = make_reddit_response(sample_posts)

    mock_response = httpx.Response(
        status_code=200,
        json=response_data,
        request=httpx.Request("GET", "https://www.reddit.com/r/nosleep/hot.json"),
    )

    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=mock_response)
    client.aclose = AsyncMock()
    return client


class TestRedditPost:
    """Tests for RedditPost dataclass."""

    def test_engagement_score(self) -> None:
        """Engagement score combines upvotes, comments, and ratio."""
        post = RedditPost(
            post_id="test1",
            subreddit="nosleep",
            title="Test post",
            selftext=None,
            score=1000,
            upvote_ratio=0.95,
            num_comments=50,
            permalink="/r/nosleep/comments/test1/test_post/",
            created_utc=1700000000,  # type: ignore[arg-type]
            url="https://reddit.com/r/nosleep/comments/test1/",
        )
        # score*0.5 + comments*2.0 + ratio*100
        expected = (1000 * 0.5) + (50 * 2.0) + (0.95 * 100)
        assert post.engagement_score == expected

    def test_source_url(self) -> None:
        """Source URL is the full Reddit link."""
        post = RedditPost(
            post_id="test1",
            subreddit="nosleep",
            title="Test",
            selftext=None,
            score=100,
            upvote_ratio=0.9,
            num_comments=10,
            permalink="/r/nosleep/comments/test1/test/",
            created_utc=1700000000,  # type: ignore[arg-type]
            url="",
        )
        assert post.source_url == "https://www.reddit.com/r/nosleep/comments/test1/test/"


class TestRedditScraper:
    """Tests for RedditScraper."""

    def test_default_subreddits(self) -> None:
        """Scraper has sensible default subreddits."""
        scraper = RedditScraper()
        assert len(scraper.subreddits) > 0
        assert "nosleep" in scraper.subreddits
        assert "TwoSentenceHorror" in scraper.subreddits

    def test_custom_subreddits(self) -> None:
        """Scraper accepts custom subreddit list."""
        custom = ["test1", "test2"]
        scraper = RedditScraper(subreddits=custom)
        assert scraper.subreddits == custom

    @pytest.mark.asyncio
    async def test_fetch_subreddit(self, mock_client: httpx.AsyncClient) -> None:
        """Fetch posts from a single subreddit."""
        scraper = RedditScraper(
            subreddits=["nosleep"],
            client=mock_client,
        )

        posts = await scraper.fetch_subreddit("nosleep")

        # Should have 3 posts (stickied one is filtered out)
        assert len(posts) == 3
        assert all(isinstance(p, RedditPost) for p in posts)

        # Verify stickied post was excluded
        post_ids = [p.post_id for p in posts]
        assert "stickied_post" not in post_ids

    @pytest.mark.asyncio
    async def test_fetch_subreddit_filters_stickied(
        self, mock_client: httpx.AsyncClient
    ) -> None:
        """Stickied posts are excluded from results."""
        scraper = RedditScraper(subreddits=["nosleep"], client=mock_client)
        posts = await scraper.fetch_subreddit("nosleep")

        for post in posts:
            assert post.post_id != "stickied_post"

    @pytest.mark.asyncio
    async def test_fetch_subreddit_http_error(self) -> None:
        """HTTP errors return empty list, don't crash."""
        mock_response = httpx.Response(
            status_code=404,
            request=httpx.Request("GET", "https://www.reddit.com/r/nonexistent/hot.json"),
        )
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(side_effect=httpx.HTTPStatusError(
            "Not Found", request=mock_response.request, response=mock_response
        ))
        client.aclose = AsyncMock()

        scraper = RedditScraper(subreddits=["nonexistent"], client=client)
        posts = await scraper.fetch_subreddit("nonexistent")
        assert posts == []

    @pytest.mark.asyncio
    async def test_fetch_subreddit_network_error(self) -> None:
        """Network errors return empty list, don't crash."""
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(side_effect=httpx.RequestError("Connection timeout"))
        client.aclose = AsyncMock()

        scraper = RedditScraper(subreddits=["nosleep"], client=client)
        posts = await scraper.fetch_subreddit("nosleep")
        assert posts == []

    @pytest.mark.asyncio
    async def test_fetch_all_sorts_by_engagement(
        self, mock_client: httpx.AsyncClient
    ) -> None:
        """fetch_all returns posts sorted by engagement score."""
        scraper = RedditScraper(subreddits=["nosleep"], client=mock_client)
        posts = await scraper.fetch_all()

        # Verify sorted descending by engagement
        scores = [p.engagement_score for p in posts]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_fetch_trending_deduplicates(
        self, mock_client: httpx.AsyncClient
    ) -> None:
        """fetch_trending deduplicates posts across strategies."""
        scraper = RedditScraper(subreddits=["nosleep"], client=mock_client)
        posts = await scraper.fetch_trending()

        # Same posts returned for hot and top (mocked), so dedup should work
        post_ids = [p.post_id for p in posts]
        assert len(post_ids) == len(set(post_ids))

    @pytest.mark.asyncio
    async def test_post_data_extraction(self, mock_client: httpx.AsyncClient) -> None:
        """Verify post fields are extracted correctly."""
        scraper = RedditScraper(subreddits=["nosleep"], client=mock_client)
        posts = await scraper.fetch_subreddit("nosleep")

        # Find specific post
        post = next(p for p in posts if p.post_id == "post3")
        assert post.title == "The previous tenant left a list of rules"
        assert post.score == 2400
        assert post.upvote_ratio == 0.98
        assert post.num_comments == 203
        assert post.flair == "Series"
        assert post.subreddit == "nosleep"
