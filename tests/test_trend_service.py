"""Tests for the trend service."""

from datetime import UTC, datetime

from content_engine.services.scrapers.reddit import RedditPost
from content_engine.services.trend_service import extract_keywords, reddit_post_to_trend


class TestExtractKeywords:
    """Tests for keyword extraction."""

    def test_extracts_meaningful_words(self) -> None:
        """Extracts words longer than 3 chars, excluding stop words."""
        post = RedditPost(
            post_id="test1",
            subreddit="nosleep",
            title="Something is watching me from the mirror every night",
            selftext=None,
            score=100,
            upvote_ratio=0.9,
            num_comments=10,
            permalink="/r/nosleep/comments/test1/",
            created_utc=datetime(2024, 1, 1, tzinfo=UTC),
            url="",
        )
        keywords = extract_keywords(post)

        # Should include meaningful words
        assert "something" in keywords
        assert "watching" in keywords
        assert "mirror" in keywords
        assert "night" in keywords

        # Should exclude stop words
        assert "from" not in keywords
        assert "the" not in keywords
        assert "every" not in keywords

    def test_includes_subreddit(self) -> None:
        """Keywords include the subreddit as context."""
        post = RedditPost(
            post_id="test1",
            subreddit="TwoSentenceHorror",
            title="Short scary story",
            selftext=None,
            score=100,
            upvote_ratio=0.9,
            num_comments=10,
            permalink="/r/TwoSentenceHorror/comments/test1/",
            created_utc=datetime(2024, 1, 1, tzinfo=UTC),
            url="",
        )
        keywords = extract_keywords(post)
        assert "r/TwoSentenceHorror" in keywords

    def test_includes_flair(self) -> None:
        """Keywords include flair text if present."""
        post = RedditPost(
            post_id="test1",
            subreddit="nosleep",
            title="A creepy story about doors",
            selftext=None,
            score=100,
            upvote_ratio=0.9,
            num_comments=10,
            permalink="/r/nosleep/comments/test1/",
            created_utc=datetime(2024, 1, 1, tzinfo=UTC),
            url="",
            flair="Series",
        )
        keywords = extract_keywords(post)
        assert "series" in keywords

    def test_deduplicates_keywords(self) -> None:
        """No duplicate keywords in output."""
        post = RedditPost(
            post_id="test1",
            subreddit="nosleep",
            title="mirror mirror on the wall mirror",
            selftext=None,
            score=100,
            upvote_ratio=0.9,
            num_comments=10,
            permalink="/r/nosleep/comments/test1/",
            created_utc=datetime(2024, 1, 1, tzinfo=UTC),
            url="",
        )
        keywords = extract_keywords(post)
        assert len(keywords) == len(set(keywords))

    def test_caps_at_15_keywords(self) -> None:
        """Keywords list is capped at 15 entries."""
        long_title = " ".join(f"word{i}xx" for i in range(30))
        post = RedditPost(
            post_id="test1",
            subreddit="nosleep",
            title=long_title,
            selftext=None,
            score=100,
            upvote_ratio=0.9,
            num_comments=10,
            permalink="/r/nosleep/comments/test1/",
            created_utc=datetime(2024, 1, 1, tzinfo=UTC),
            url="",
        )
        keywords = extract_keywords(post)
        assert len(keywords) <= 15


class TestRedditPostToTrend:
    """Tests for converting RedditPost to Trend model."""

    def test_converts_fields_correctly(self) -> None:
        """All fields map to Trend model correctly."""
        post = RedditPost(
            post_id="abc123",
            subreddit="nosleep",
            title="The thing under my bed spoke last night",
            selftext="It started when I was five years old...",
            score=1500,
            upvote_ratio=0.96,
            num_comments=120,
            permalink="/r/nosleep/comments/abc123/the_thing_under/",
            created_utc=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
            url="https://reddit.com/r/nosleep/comments/abc123/",
            flair="Series",
        )

        trend = reddit_post_to_trend(post)

        assert trend.source == "reddit"
        assert trend.source_url == "https://www.reddit.com/r/nosleep/comments/abc123/the_thing_under/"
        assert trend.title == "The thing under my bed spoke last night"
        assert trend.description == "It started when I was five years old..."
        assert trend.category == "r/nosleep"
        assert trend.engagement_score == post.engagement_score
        assert trend.trending_at == datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        assert trend.keywords is not None
        assert len(trend.keywords) > 0

    def test_handles_none_selftext(self) -> None:
        """Post without selftext gets None description."""
        post = RedditPost(
            post_id="abc123",
            subreddit="creepy",
            title="Creepy photo from abandoned hospital",
            selftext=None,
            score=500,
            upvote_ratio=0.92,
            num_comments=30,
            permalink="/r/creepy/comments/abc123/",
            created_utc=datetime(2024, 1, 1, tzinfo=UTC),
            url="",
        )

        trend = reddit_post_to_trend(post)
        assert trend.description is None

    def test_truncates_long_selftext(self) -> None:
        """Very long selftext is truncated to 2000 chars."""
        post = RedditPost(
            post_id="abc123",
            subreddit="nosleep",
            title="A very long story",
            selftext="x" * 5000,
            score=100,
            upvote_ratio=0.9,
            num_comments=10,
            permalink="/r/nosleep/comments/abc123/",
            created_utc=datetime(2024, 1, 1, tzinfo=UTC),
            url="",
        )

        trend = reddit_post_to_trend(post)
        assert trend.description is not None
        assert len(trend.description) == 2000
