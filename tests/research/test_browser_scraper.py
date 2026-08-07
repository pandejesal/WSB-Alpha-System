import pytest
from unittest.mock import patch, Mock
import requests
from src.research.browser_scraper import fetch_headlines, score_text

@patch("src.research.browser_scraper.requests.get")
def test_fetch_headlines_success(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = """
    <rss><channel>
        <title>Yahoo Finance</title>
        <item><title><![CDATA[Apple stock soars]]></title></item>
        <item><title>Microsoft announces new product</title></item>
    </channel></rss>
    """
    mock_get.return_value = mock_response

    headlines = fetch_headlines("AAPL")

    assert len(headlines) == 2
    assert "Apple stock soars" in headlines
    assert "Microsoft announces new product" in headlines

@patch("src.research.browser_scraper.requests.get")
def test_fetch_headlines_failure_degradation(mock_get):
    # Simulate a network error
    mock_get.side_effect = requests.exceptions.Timeout("Timeout")

    # Should not crash, just return empty list
    headlines = fetch_headlines("AAPL")

    assert headlines == []

def test_score_text_positive():
    texts = [
        "The company saw strong growth and profit this quarter.",
        "Investors say buy this bull stock as it continues to soar."
    ]
    result = score_text(texts)

    assert result["classification"] == "positive"
    assert result["net_score"] > 0

def test_score_text_negative():
    texts = [
        "Stock takes a plunge after weak earnings miss.",
        "Bear market causes decline and sell off."
    ]
    result = score_text(texts)

    assert result["classification"] == "negative"
    assert result["net_score"] < 0

def test_score_text_empty():
    result = score_text([])
    assert result["classification"] == "neutral"
    assert result["net_score"] == 0.0
