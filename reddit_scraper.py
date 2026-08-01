import os
import time
import random
import asyncio
import hashlib
import sqlite3
import logging
import datetime
from typing import List, Dict

try:
    import praw
    import prawcore.exceptions
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False

logger = logging.getLogger(__name__)

# Configure SQLite Cache
CACHE_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seen_posts.db")

def _init_db():
    """
    Initializes the SQLite database used for deduplication.
    This database acts as a local cache to ensure we do not process
    the same Reddit post multiple times, saving FinBERT inference time
    and preventing double-counting sentiment.
    """
    with sqlite3.connect(CACHE_DB_PATH) as conn:
        cursor = conn.cursor()
        # The primary key is the hashed Reddit ID for faster lookups and minimal storage overhead
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS seen_posts (
                post_hash TEXT PRIMARY KEY,
                post_id TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()

def _is_post_seen(conn, post_id: str) -> bool:
    """
    Checks if a post has been seen by hashing its ID.
    Hashing the ID provides a fixed-length string for the primary key
    which makes SQLite index lookups incredibly fast.
    """
    post_hash = hashlib.sha256(post_id.encode('utf-8')).hexdigest()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM seen_posts WHERE post_hash = ?", (post_hash,))
    result = cursor.fetchone()
    return result is not None

def _mark_post_seen(conn, post_id: str):
    """
    Marks a post as seen by storing its hashed ID.
    INSERT OR IGNORE is used to gracefully handle any race conditions
    where the ID might already have been inserted.
    """
    post_hash = hashlib.sha256(post_id.encode('utf-8')).hexdigest()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO seen_posts (post_hash, post_id) VALUES (?, ?)",
        (post_hash, post_id)
    )
    conn.commit()

async def fetch_reddit_data_chunked(max_items: int = 1000, target_year: int = None) -> List[Dict]:
    """
    Fetches Reddit data using Time-Window Chunking (4-hour intervals) to bypass the 1000 post limit.
    Wraps asynchronous execution for praw block safe queries.

    This function implements institutional-grade Anti-Ban and data-integrity features:
    1. Smart Rate-Limiting & Exponential Backoff: Captures prawcore.exceptions.TooManyRequests
       and waits progressively longer (60s, 120s, etc.) before retrying.
    2. Time-Window Chunking: Splits queries into 4-hour blocks using Unix timestamps to overcome
       the Reddit search limit of 1000 items.
    3. Natural Throttling: Uses asyncio.sleep with random delays to mimic human paging.
    """
    _init_db()

    if not PRAW_AVAILABLE:
        logger.error("PRAW is not installed. Returning empty items.")
        return []

    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")

    if not client_id or not client_secret:
        logger.warning("REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET not set. Authentication required.")
        return []

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent="WSB-Alpha-System"
    )

    items = []

    # Determine the time window for chunking
    if target_year:
        end_time = datetime.datetime(target_year, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc)
        start_bound = datetime.datetime(target_year, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    else:
        end_time = datetime.datetime.now(datetime.timezone.utc)
        start_bound = end_time - datetime.timedelta(days=365 * 10) # 10 years back max

    current_end = end_time
    # Use a 4-hour chunking delta to ensure we never hit the 1,000 post cap within a single query
    chunk_delta = datetime.timedelta(hours=4)
    total_fetched = 0
    consecutive_empty_chunks = 0
    max_empty_chunks = 100 # Stop if we have gone a long time with no posts to prevent infinite looping

    logger.info(f"Starting PRAW scraper with Time-Window Chunking (4-hour windows). Target items: {max_items}")

    with sqlite3.connect(CACHE_DB_PATH) as conn:
        while total_fetched < max_items and current_end > start_bound:
            current_start = current_end - chunk_delta

            start_ts = int(current_start.timestamp())
            end_ts = int(current_end.timestamp())

            query = f"flair:DD timestamp:{start_ts}..{end_ts}"

            # Define the blocking sync function to be run in a separate thread
            # This prevents PRAW's synchronous network calls from blocking the main asyncio event loop
            def _fetch_sync():
                submissions_list = []
                submissions = reddit.subreddit("wallstreetbets").search(query, sort='new', limit=1000)
                for submission in submissions:
                    submissions_list.append(submission)
                return submissions_list

            # Setup variables for Exponential Backoff algorithm
            backoff = 60
            max_retries = 5
            retries = 0
            success = False
            submissions_chunk = []

            # Retry loop with Exponential Backoff for handling rate limits
            while retries < max_retries and not success:
                try:
                    # Execute the blocking PRAW call in a background thread
                    submissions_chunk = await asyncio.to_thread(_fetch_sync)
                    success = True
                except prawcore.exceptions.TooManyRequests as e:
                    # Exponential Backoff algorithm: if rate limit is hit, wait 60s, then 120s, etc.
                    logger.warning(f"Rate limit hit! TooManyRequests. Sleeping for {backoff} seconds... (Retry {retries+1}/{max_retries})")
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    retries += 1
                except Exception as e:
                    logger.error(f"Error fetching chunk from PRAW: {e}")
                    break # Break out of retry loop for other unexpected errors

            if success:
                chunk_items = 0
                for submission in submissions_chunk:
                    # Check SQLite cache to avoid double-processing and wasting FinBERT compute
                    if _is_post_seen(conn, submission.id):
                        continue

                    items.append({
                        "id": submission.id,
                        "title": submission.title,
                        "body": submission.selftext,
                        "createdAt": int(submission.created_utc),
                        "permalink": submission.permalink,
                        "score": submission.score,
                        "num_comments": submission.num_comments
                    })
                    # Mark this post as seen in the SQLite cache immediately
                    _mark_post_seen(conn, submission.id)
                    chunk_items += 1
                    total_fetched += 1

                    if total_fetched >= max_items:
                        break

                if chunk_items == 0:
                    consecutive_empty_chunks += 1
                else:
                    consecutive_empty_chunks = 0
                    logger.info(f"Fetched {chunk_items} posts in window {current_start.strftime('%Y-%m-%d %H:%M')} to {current_end.strftime('%Y-%m-%d %H:%M')}. Total: {total_fetched}/{max_items}")

                if consecutive_empty_chunks > max_empty_chunks:
                    logger.info("Reached maximum empty time chunks. Stopping search.")
                    break

            else:
                logger.error("Failed to fetch chunk after max retries.")
                break

            # Move the time window back by 4 hours for the next chunk
            current_end = current_start

            # Natural throttle: add random jitter (1.5s to 3.5s) between pagination queries
            # to mimic human pacing and reduce the likelihood of IP bans.
            sleep_time = random.uniform(1.5, 3.5)
            await asyncio.sleep(sleep_time)

    logger.info(f"Retrieved {len(items)} raw metadata items from PRAW using chunking.")
    return items

def fetch_reddit_data_sync(max_items: int = 1000, target_year: int = None) -> List[Dict]:
    """
    Synchronous wrapper for fetch_reddit_data_chunked.
    This provides a simplified interface for scripts that do not require
    an active asyncio event loop, while still utilizing the robust async
    logic internally.
    """
    return asyncio.run(fetch_reddit_data_chunked(max_items, target_year))
