import pytest
from unittest.mock import patch, MagicMock
import requests

from src.research.browser_scraper import fetch_headlines, score_text

class MockResponse:
    def __init__(self, text, status_code):
        self.text = text
        self.status_code = status_code

def test_fetch_headlines_success():
    mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Yahoo Finance: AAPL</title>
        <item>
          <title><![CDATA[Apple Surges on Earnings]]></title>
        </item>
        <item>
          <title>New iPhone is a hit</title>
        </item>
      </channel>
    </rss>
    """
    with patch('requests.get', return_value=MockResponse(mock_xml, 200)):
        headlines = fetch_headlines("AAPL")

    assert len(headlines) == 2
    assert headlines[0] == "Apple Surges on Earnings"
    assert headlines[1] == "New iPhone is a hit"

def test_fetch_headlines_retry_logic():
    # Sequence of responses: 500, 429, then 200
    mock_responses = [
        MockResponse("Error", 500),
        MockResponse("Too Many Requests", 429),
        MockResponse("<item><title>Finally succeeded</title></item>", 200)
    ]

    with patch('requests.get', side_effect=mock_responses) as mock_get:
        # Patch sleep to not actually wait during tests
        with patch('time.sleep', return_value=None):
            headlines = fetch_headlines("TSLA")

    assert mock_get.call_count == 3
    assert len(headlines) == 1
    assert headlines[0] == "Finally succeeded"

def test_fetch_headlines_degrades_gracefully_on_timeout():
    with patch('requests.get', side_effect=requests.exceptions.Timeout("Timed out")):
        with patch('time.sleep', return_value=None):
            headlines = fetch_headlines("NVDA")

    # Should return empty list, not crash
    assert headlines == []

def test_fetch_headlines_degrades_gracefully_on_404():
    with patch('requests.get', return_value=MockResponse("Not Found", 404)):
        headlines = fetch_headlines("INVALID")

    # Should return empty list, not crash
    assert headlines == []

def test_score_text_positive():
    texts = [
        "The company saw a massive surge in profit today.",
        "They beat expectations and will grow fast."
    ]
    res = score_text(texts)

    assert res["classification"] == "positive"
    assert res["positive_ratio"] > 0
    assert res["negative_ratio"] == 0.0
    assert res["net_score"] > 0

def test_score_text_negative():
    texts = [
        "Shares plunge following a massive miss on earnings.",
        "The drop is a failure."
    ]
    res = score_text(texts)

    assert res["classification"] == "negative"
    assert res["negative_ratio"] > 0
    assert res["positive_ratio"] == 0.0
    assert res["net_score"] < 0

def test_score_text_neutral_and_empty():
    res_empty = score_text([])
    assert res_empty["classification"] == "neutral"
    assert res_empty["net_score"] == 0.0

    # Neutral text (no lexicon matches)
    res_neutral = score_text(["The stock market is open today at 9:30 AM."])
    assert res_neutral["classification"] == "neutral"
    assert res_neutral["net_score"] == 0.0
    assert res_neutral["positive_ratio"] == 0.0
    assert res_neutral["negative_ratio"] == 0.0

def test_score_text_graceful_exception():
    # Pass something that triggers exception (e.g., None instead of string)
    res = score_text([None])
    assert res["classification"] == "neutral"
    assert res["net_score"] == 0.0
