import pytest
from unittest.mock import patch
from src.research.debate_engine import DebateEngine

def test_debate_engine_bullish_consensus():
    engine = DebateEngine()

    mock_headlines = ["Great surge in profit", "Stock hits new high and beats estimates"]
    mock_score = {
        "positive_ratio": 0.8,
        "negative_ratio": 0.0,
        "net_score": 0.8,
        "classification": "positive"
    }

    with patch('src.research.debate_engine.fetch_headlines', return_value=mock_headlines), \
         patch('src.research.debate_engine.score_text', return_value=mock_score):

         result = engine.run_debate("AAPL")

    assert result["ticker"] == "AAPL"
    assert result["stance"] == "bullish"
    assert result["score"] > 0.33

    agents = result["agents"]
    assert len(agents) == 3

    bull_agent = next(a for a in agents if a["role"] == "bull")
    assert bull_agent["stance"] == "bullish"

    bear_agent = next(a for a in agents if a["role"] == "bear")
    assert bear_agent["stance"] == "neutral"  # Since classification is positive

def test_debate_engine_bearish_consensus():
    engine = DebateEngine()

    mock_headlines = ["Massive plunge and loss", "Stock crashes after fail"]
    mock_score = {
        "positive_ratio": 0.0,
        "negative_ratio": 0.9,
        "net_score": -0.9,
        "classification": "negative"
    }

    with patch('src.research.debate_engine.fetch_headlines', return_value=mock_headlines), \
         patch('src.research.debate_engine.score_text', return_value=mock_score):

         result = engine.run_debate("TSLA")

    assert result["ticker"] == "TSLA"
    assert result["stance"] == "bearish"
    assert result["score"] < -0.33

    agents = result["agents"]
    bear_agent = next(a for a in agents if a["role"] == "bear")
    assert bear_agent["stance"] == "bearish"

def test_debate_engine_empty_headlines_graceful_degradation():
    engine = DebateEngine()

    mock_headlines = []
    mock_score = {
        "positive_ratio": 0.0,
        "negative_ratio": 0.0,
        "net_score": 0.0,
        "classification": "neutral"
    }

    with patch('src.research.debate_engine.fetch_headlines', return_value=mock_headlines), \
         patch('src.research.debate_engine.score_text', return_value=mock_score):

         result = engine.run_debate("UNKNOWN")

    assert result["ticker"] == "UNKNOWN"
    assert result["stance"] == "neutral"
    assert result["score"] == 0.0

    # Check that reasoning notes the lack of data
    for agent in result["agents"]:
        if agent["role"] == "neutral":
            assert agent["confidence"] == 0.9
            assert "Complete lack of market news" in agent["reasoning"]

def test_debate_engine_agent_exception_handled():
    engine = DebateEngine()

    mock_headlines = ["Normal news"]
    mock_score = {
        "positive_ratio": 0.1,
        "negative_ratio": 0.1,
        "net_score": 0.0,
        "classification": "neutral"
    }

    with patch('src.research.debate_engine.fetch_headlines', return_value=mock_headlines), \
         patch('src.research.debate_engine.score_text', return_value=mock_score), \
         patch.object(engine, '_simulate_bear_agent', side_effect=Exception("Simulated crash")):

         # The bear agent crashes, but the overall debate should still run and return
         result = engine.run_debate("MSFT")

    assert result["ticker"] == "MSFT"
    assert len(result["agents"]) == 2 # Only bull and neutral survived
    roles = [a["role"] for a in result["agents"]]
    assert "bear" not in roles
    assert "bull" in roles
    assert "neutral" in roles
