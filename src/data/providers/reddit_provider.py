import logging

import pandas as pd
import pandera as pa
import praw

from src.data.cache_engine import CacheEngine
from src.data.schemas import SentimentPostSchema
from src.utils.config import config

from .base import BaseDataProvider

logger = logging.getLogger(__name__)

class RedditProvider(BaseDataProvider):
    def __init__(self, cache_engine: CacheEngine = None):
        self.cache = cache_engine or CacheEngine()
        self.reddit = None
        if config.api_keys.reddit_client_id and config.api_keys.reddit_client_secret.get_secret_value():
            try:
                self.reddit = praw.Reddit(
                    client_id=config.api_keys.reddit_client_id,
                    client_secret=config.api_keys.reddit_client_secret.get_secret_value(),
                    user_agent="WSB-Alpha-System/1.0"
                )
            except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
                logger.error(f"Failed to initialize PRAW: {e}")

    def fetch_ohlcv(self, tickers: list[str], start_date: str, end_date: str) -> pd.DataFrame:
        raise NotImplementedError("Reddit does not provide OHLCV data.")


    @pa.check_types
    def fetch_sentiment_feed(self, limit: int) -> pa.typing.DataFrame[SentimentPostSchema]:
        cached = self.cache.get_sentiment(limit)
        if not cached.empty and len(cached) >= limit:
            # Type casting to match schema exactly
            return cached.head(limit)

        posts = []
        if self.reddit:
            try:
                subreddit = self.reddit.subreddit('wallstreetbets')
                for submission in subreddit.hot(limit=limit):
                    posts.append({
                        "post_id": str(submission.id),
                        "post_date": pd.to_datetime(submission.created_utc, unit='s'),
                        "ticker": "UNKNOWN", # Ticker extraction runs later
                        "title": submission.title,
                        "sentiment_score": 0.0, # Filled later
                        "content": submission.selftext,
                        "score": float(submission.score)
                    })
            except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
                logger.warning(f"PRAW fetch failed, falling back to RSS: {e}")
                posts = self._fetch_rss_fallback(limit)
        else:
            posts = self._fetch_rss_fallback(limit)

        df = pd.DataFrame(posts)
        if not df.empty:
            self.cache.store_sentiment(df)
        return df

    def _fetch_rss_fallback(self, limit: int) -> list:
        import time

        import feedparser
        posts = []
        try:
            feed = feedparser.parse("https://www.reddit.com/r/wallstreetbets/hot.rss")
            for entry in feed.entries[:limit]:
                from calendar import timegm
                created_utc = timegm(entry.published_parsed) if entry.published_parsed else time.time()
                posts.append({
                    "post_id": str(entry.id.split('_')[-1]),
                    "post_date": pd.to_datetime(created_utc, unit='s'),
                    "ticker": "UNKNOWN",
                    "title": entry.title,
                    "sentiment_score": 0.0,
                    "content": entry.summary,
                    "score": 0.0
                })
        except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
            logger.debug(f"Failed to parse reddit post: {e}")
        return posts
