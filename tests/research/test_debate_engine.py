import pytest
from src.research.debate_engine import DebateEngine

@pytest.fixture
def debate_engine():
    return DebateEngine()

def test_debate_bullish_consensus(debate_engine):
    headlines = ["Strong growth", "Exceeds expectations"]
    base_score = {
        "classification": "positive",
        "positive_ratio": 0.8,
        "negative_ratio": 0.0,
        "net_score": 0.8
    }

    res = debate_engine.run_debate("AAPL", headlines, base_score)

    assert res["stance"] == "bullish"
    assert res["score"] > 0.33
    assert len(res["agents"]) == 3
    assert any("Bull Agent" in r for r in res["reasoning"])

def test_debate_bearish_consensus(debate_engine):
    headlines = ["Massive plunge", "Fails to meet expectations"]
    base_score = {
        "classification": "negative",
        "positive_ratio": 0.0,
        "negative_ratio": 0.9,
        "net_score": -0.9
    }

    res = debate_engine.run_debate("TSLA", headlines, base_score)

    assert res["stance"] == "bearish"
    assert res["score"] < -0.33
    assert len(res["agents"]) == 3
    assert any("Bear Agent" in r for r in res["reasoning"])

def test_debate_neutral_and_empty(debate_engine):
    # Empty case
    res = debate_engine.run_debate("UNKNOWN", [], {})
    assert res["stance"] == "neutral"
    assert res["score"] == 0.0
    assert "Complete lack of market news" in res["reasoning"][2]

    # Neutral base score
    base_score = {
        "classification": "neutral",
        "positive_ratio": 0.1,
        "negative_ratio": 0.1,
        "net_score": 0.0
    }
    res = debate_engine.run_debate("SPY", ["Normal day in the market"], base_score)
    assert res["stance"] == "neutral"
    assert -0.33 <= res["score"] <= 0.33
