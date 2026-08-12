import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

POSITIVE_WORDS = {"up", "high", "growth", "beat", "profit", "gain", "buy", "bull", "strong", "positive", "exceed", "soar"}
NEGATIVE_WORDS = {"plunge", "miss", "fall", "down", "low", "loss", "decline", "sell", "bear", "weak", "negative", "drop", "crash", "fail", "missed"}

def fetch_headlines(ticker: str) -> list[str]:
    """
    Fetches lightweight market/news headlines for a ticker using Yahoo Finance RSS feeds.
    Includes HTTP retries with exponential backoff on 429/5xx, and a 5-second timeout.
    Gracefully degrades by returning an empty list on any failure.
    """
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"

    max_retries = 3
    base_delay = 1.0

    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=5.0)

            if response.status_code == 200:
                # Lightweight XML parsing to avoid heavy deps like lxml/bs4 if possible
                # Since the project already has beautifulsoup4 (from requirements.txt), we can safely use standard regex or string matching to keep it lightweight.
                # Just doing a simple string split to extract <title> tags inside <item>
                headlines = []
                content = response.text

                # A very basic parse without importing xml/bs4 to stay perfectly resilient
                # We skip the main channel title and grab the item titles
                items = content.split("<item>")
                for item in items[1:]:
                    title_start = item.find("<title>")
                    title_end = item.find("</title>")
                    if title_start != -1 and title_end != -1:
                        # Add 7 to skip "<title>"
                        title = item[title_start + 7:title_end]
                        # Remove basic CDATA wraps if present
                        title = title.replace("<![CDATA[", "").replace("]]>", "").strip()
                        if title:
                            headlines.append(title)

                return headlines

            elif response.status_code in (429, 500, 502, 503, 504):
                # Rate limit or server error - apply backoff
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Fetch failed with {response.status_code} for {ticker}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                # Hard failure on 404, etc. Do not retry, just degrade.
                logger.warning(f"Fetch failed with unrecoverable status {response.status_code} for {ticker}.")
                return []

        except requests.exceptions.RequestException as e:
            # Network issue, timeout, etc.
            delay = base_delay * (2 ** attempt)
            logger.warning(f"Network error fetching {ticker}: {e}. Retrying in {delay}s...")
            time.sleep(delay)
        except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
            # Absolute failsafe - NEVER crash the caller
            logger.error(f"Unexpected error parsing headlines for {ticker}: {e}")
            return []

    # Exhausted retries
    logger.warning(f"Exhausted retries fetching headlines for {ticker}.")
    return []

def score_text(texts: list[str]) -> dict[str, Any]:
    """
    Produces a simple positive/neutral/negative sentiment score with a tiny lexicon.
    Gracefully handles empty lists and exceptions.
    Returns:
        {"positive_ratio": float, "negative_ratio": float, "net_score": float, "classification": str}
    """
    if not texts:
        return {
            "positive_ratio": 0.0,
            "negative_ratio": 0.0,
            "net_score": 0.0,
            "classification": "neutral"
        }

    try:
        pos_hits = 0
        neg_hits = 0
        total_words = 0

        for text in texts:
            # Basic tokenization
            words = text.lower().replace(",", "").replace(".", "").replace("!", "").replace("?", "").split()
            total_words += len(words)
            for word in words:
                if word in POSITIVE_WORDS:
                    pos_hits += 1
                elif word in NEGATIVE_WORDS:
                    neg_hits += 1

        if total_words == 0:
            return {
                "positive_ratio": 0.0,
                "negative_ratio": 0.0,
                "net_score": 0.0,
                "classification": "neutral"
            }

        pos_ratio = pos_hits / total_words
        neg_ratio = neg_hits / total_words
        net_score = pos_ratio - neg_ratio

        classification = "neutral"
        if net_score > 0.01:
            classification = "positive"
        elif net_score < -0.01:
            classification = "negative"

        return {
            "positive_ratio": round(pos_ratio, 4),
            "negative_ratio": round(neg_ratio, 4),
            "net_score": round(net_score, 4),
            "classification": classification
        }
    except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
        logger.error(f"Unexpected error scoring text: {e}")
        return {
            "positive_ratio": 0.0,
            "negative_ratio": 0.0,
            "net_score": 0.0,
            "classification": "neutral"
        }
