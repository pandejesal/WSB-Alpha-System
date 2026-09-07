"""Tests for FinGPT sentiment factor port.

Tests cover: negation handling, intensifier application, neutral detection,
bounds validation, and evaluation harness reproducibility.
"""

from src.signals.fingpt_sentiment import (
    POSITIVE_LEXICON,
    NEGATIVE_LEXICON,
    score_sentiment,
    score_batch,
    map_sentiment_to_signal,
    generate_synthetic_sentiment,
    run_evaluation,
    SAMPLE_EVAL_SET,
)


class TestSentimentBounds:
    """Test that sentiment scores stay within [-1, 1]."""
    
    def test_extreme_positive_text(self):
        text = "extremely very massively bullish surge rally breakout record high"
        result = score_sentiment(text)
        assert -1.0 <= result["score"] <= 1.0
        assert result["label"] in ("positive", "negative", "neutral")
    
    def test_extreme_negative_text(self):
        text = "extremely very massively bearish crash plunge collapse record low"
        result = score_sentiment(text)
        assert -1.0 <= result["score"] <= 1.0
    
    def test_empty_string(self):
        result = score_sentiment("")
        assert result["score"] == 0.0
        assert result["label"] == "neutral"
        assert result["confidence"] == 0.0
    
    def test_whitespace_only(self):
        result = score_sentiment("   \t\n  ")
        assert result["score"] == 0.0
        assert result["label"] == "neutral"


class TestNegationHandling:
    """Test that negators flip sentiment polarity."""
    
    def test_positive_negated(self):
        result = score_sentiment("not positive news")
        assert result["negated"] is True
        # Negated positive should be negative or neutral
        assert result["score"] <= 0.1
    
    def test_negative_negated(self):
        result = score_sentiment("no crash expected")
        assert result["negated"] is True
        # Negated negative should be positive or neutral
        assert result["score"] >= -0.1
    
    def test_very_negative_negated(self):
        result = score_sentiment("not a disaster")
        assert result["negated"] is True
        assert result["score"] >= 0.0
    
    def test_negation_detection(self):
        result = score_sentiment("the stock is not crashing")
        assert result["negated"] is True
    
    def test_no_negation_without_marker(self):
        result = score_sentiment("stock surges to record high")
        assert result["negated"] is False


class TestIntensifierHandling:
    """Test that intensifiers amplify sentiment."""
    
    def test_intensifier_amplifies_positive(self):
        base = score_sentiment("stock rises")
        intensified = score_sentiment("stock rises significantly")
        # Intensified should have higher absolute score
        assert abs(intensified["score"]) >= abs(base["score"])
    
    def test_extreme_intensifier(self):
        base = score_sentiment("gain")
        extreme = score_sentiment("extremely massive huge gain")
        assert abs(extreme["score"]) >= abs(base["score"])
    
    def test_intensifier_capped(self):
        text = "very extremely massively dramatically significantly unprecedented record huge massive major"
        result = score_sentiment(text)
        # Even with many intensifiers, score should be in bounds
        assert -1.0 <= result["score"] <= 1.0


class TestNeutralDetection:
    """Test that truly neutral text is classified as neutral."""
    
    def test_earnings_in_line(self):
        result = score_sentiment("Company reports in-line earnings")
        assert result["label"] == "neutral"
        assert abs(result["score"]) < 0.5
    
    def test_no_sentiment_words(self):
        result = score_sentiment("The company issued a statement today")
        assert result["label"] == "neutral"
    
    def test_mixed_signals(self):
        result = score_sentiment("profit up but revenue down")
        # Should be close to neutral due to mixed signals
        assert abs(result["score"]) < 0.5


class TestFactorMapping:
    """Test mapping sentiment score to trading signal."""
    
    def test_strong_positive_maps_to_long(self):
        result = map_sentiment_to_signal(0.8)
        assert result["signal"] == "LONG"
        assert result["confidence"] > 0.0
    
    def test_strong_negative_maps_to_flat(self):
        result = map_sentiment_to_signal(-0.8)
        assert result["signal"] == "FLAT"
        assert result["confidence"] > 0.0
    
    def test_neutral_maps_to_flat(self):
        result = map_sentiment_to_signal(0.0)
        assert result["signal"] == "FLAT"
        assert result["confidence"] == 0.3
    
    def test_boundary_values(self):
        # At threshold boundaries
        result_pos = map_sentiment_to_signal(0.2)
        result_neg = map_sentiment_to_signal(-0.2)
        assert result_pos["signal"] in ("LONG", "FLAT")
        assert result_neg["signal"] in ("LONG", "FLAT")


class TestSyntheticSentiment:
    """Test synthetic sentiment generation (for backtesting only)."""
    
    def test_returns_list_same_length(self):
        returns = [0.01, -0.02, 0.005, 0.015, -0.01]
        sentiments = generate_synthetic_sentiment(returns, lookback=3)
        assert len(sentiments) == len(returns)
    
    def test_values_in_bounds(self):
        returns = [0.01, -0.02, 0.005, 0.015, -0.01, 0.02, -0.03]
        sentiments = generate_synthetic_sentiment(returns, lookback=3)
        for s in sentiments:
            assert -1.0 <= s <= 1.0
    
    def test_positive_returns_positive_sentiment(self):
        # Strong positive returns should generally produce positive sentiment
        returns = [0.02, 0.03, 0.025, 0.02, 0.035, 0.03, 0.025]
        sentiments = generate_synthetic_sentiment(returns, lookback=3, noise_std=0.01)
        # Most should be positive
        positive_count = sum(1 for s in sentiments if s > 0)
        assert positive_count > len(sentiments) / 2


class TestBatchScoring:
    """Test batch scoring functionality."""
    
    def test_batch_same_as_individual(self):
        texts = [
            "Stock surges to record high",
            "Company misses earnings, shares plunge",
            "Stock holds steady amid mixed signals",
        ]
        batch_results = score_batch(texts)
        individual_results = [score_sentiment(t) for t in texts]
        
        for batch, individual in zip(batch_results, individual_results):
            assert batch["score"] == individual["score"]
            assert batch["label"] == individual["label"]


class TestEvaluationHarness:
    """Test evaluation harness reproducibility."""
    
    def test_evaluation_runs_without_error(self):
        result = run_evaluation()
        assert "accuracy" in result
        assert "macro_f1" in result
        assert "confusion" in result
        assert "per_label" in result
    
    def test_evaluation_metrics_in_range(self):
        result = run_evaluation()
        assert 0.0 <= result["accuracy"] <= 1.0
        assert 0.0 <= result["macro_f1"] <= 1.0
        
        for label, metrics in result["per_label"].items():
            assert 0.0 <= metrics["precision"] <= 1.0
            assert 0.0 <= metrics["recall"] <= 1.0
            assert 0.0 <= metrics["f1"] <= 1.0
    
    def test_sample_set_size(self):
        assert len(SAMPLE_EVAL_SET) >= 30, "Sample set must have at least 30 sentences"
    
    def test_sample_set_labels_balanced(self):
        labels = [s["label"] for s in SAMPLE_EVAL_SET]
        from collections import Counter
        counts = Counter(labels)
        # Each label should have at least 5 examples
        for label in ["positive", "negative", "neutral"]:
            assert counts[label] >= 5, f"Need at least 5 '{label}' examples"
    
    def test_evaluation_deterministic(self):
        # Run twice, should get same results (no randomness in scoring)
        result1 = run_evaluation()
        result2 = run_evaluation()
        assert result1["accuracy"] == result2["accuracy"]
        assert result1["macro_f1"] == result2["macro_f1"]


class TestLexiconIntegrity:
    """Test that lexicons are properly structured."""
    
    def test_positive_lexicon_weights_in_range(self):
        for word, weight in POSITIVE_LEXICON.items():
            assert 0.0 <= weight <= 1.0, f"Weight for '{word}' out of range"
    
    def test_negative_lexicon_weights_in_range(self):
        for word, weight in NEGATIVE_LEXICON.items():
            assert 0.0 <= weight <= 1.0, f"Weight for '{word}' out of range"
    
    def test_no_lexicon_overlap(self):
        pos_words = set(POSITIVE_LEXICON.keys())
        neg_words = set(NEGATIVE_LEXICON.keys())
        overlap = pos_words & neg_words
        assert len(overlap) == 0, f"Words in both lexicons: {overlap}"


class TestFullPipeline:
    """Integration tests for the full sentiment pipeline."""
    
    def test_headline_to_signal(self):
        """Test complete flow: headline → sentiment → signal."""
        headline = "Company beats earnings, stock surges to record high"
        
        # Step 1: Score sentiment
        sentiment = score_sentiment(headline)
        assert sentiment["label"] == "positive"
        assert sentiment["score"] > 0
        
        # Step 2: Map to signal
        signal = map_sentiment_to_signal(sentiment["score"])
        assert signal["signal"] == "LONG"
    
    def test_negative_headline_to_signal(self):
        """Test negative headline flow."""
        headline = "Company misses earnings, shares crash on recession fears"
        
        sentiment = score_sentiment(headline)
        assert sentiment["label"] == "negative"
        assert sentiment["score"] < 0
        
        signal = map_sentiment_to_signal(sentiment["score"])
        assert signal["signal"] == "FLAT"
