"""FinGPT Sentiment Factor Port — Lexicon-based financial sentiment scorer.

Provides sentiment scoring for financial text using a finance-specific lexicon
with negation handling and intensifier detection. Maps sentiment scores to
trading signals (LONG/FLAT) for SPY timing overlay.

Usage:
    from src.signals.fingpt_sentiment import score_sentiment, map_sentiment_to_signal

    result = score_sentiment("Company beats earnings, stock surges")
    signal = map_sentiment_to_signal(result["score"])

Note:
    This is a rule-based sentiment scorer, NOT an LLM-based model.
    Backtest results using synthetic sentiment are FRAUDULENT for alpha claims.
"""

from __future__ import annotations

from typing import List, Dict, Tuple


# === Finance-specific sentiment lexicons ===

POSITIVE_LEXICON: Dict[str, float] = {
    # Strong positive (0.7-1.0)
    "surge": 0.85, "rally": 0.8, "soar": 0.85, "breakout": 0.75,
    "record high": 0.9, "all-time high": 0.9, "upgrade": 0.7,
    "outperform": 0.75, "beat": 0.7, "beats": 0.75, "exceeded": 0.7,
    "exceeds": 0.75, "exceeding": 0.7, "beat expectations": 0.8,
    "blowout": 0.85, "blockbuster": 0.8, "explosive": 0.8,
    "moon": 0.7, "bullish": 0.75, "boom": 0.75, "thrive": 0.7,
    "surpass": 0.7, "trounce": 0.8, "crush": 0.8,
    # Medium positive (0.4-0.69)
    "rise": 0.55, "rises": 0.55, "rising": 0.55, "rose": 0.55,
    "gain": 0.5, "gains": 0.5, "gained": 0.5, "gaining": 0.5,
    "jump": 0.6, "jumps": 0.6, "jumped": 0.6, "spike": 0.6,
    "spikes": 0.6, "recovery": 0.5, "rebound": 0.55, "recovery rally": 0.6,
    "growth": 0.5, "profit": 0.45, "profitable": 0.5, "profitability": 0.5,
    "dividend": 0.4, "yield": 0.4, "upside": 0.5, "uptrend": 0.55,
    "strong": 0.45, "strength": 0.45, "positive": 0.5, "optimism": 0.5,
    "optimistic": 0.55, "confidence": 0.4, "upgrade to buy": 0.7,
    "buy rating": 0.6, "strong buy": 0.7,
    # Mild positive (0.2-0.39)
    "stable": 0.25, "stability": 0.25, "steady": 0.25, "improve": 0.3,
    "improvement": 0.3, "improving": 0.3, "positive momentum": 0.35,
    "support": 0.25, "up": 0.3, "higher": 0.25, "above": 0.2,
    "beat estimates": 0.6, "beat forecast": 0.6,
}

NEGATIVE_LEXICON: Dict[str, float] = {
    # Strong negative (0.7-1.0)
    "crash": 0.9, "crashes": 0.9, "crashing": 0.85, "collapse": 0.85,
    "plunge": 0.85, "plunges": 0.85, "plunging": 0.85,
    "record low": 0.9, "all-time low": 0.9, "downgrade": 0.7,
    "underperform": 0.75, "miss": 0.7, "missed": 0.75, "misses": 0.7,
    "missed expectations": 0.8, "fell short": 0.75, "disappointing": 0.7,
    "disappointment": 0.7, "shock": 0.7, "shocking": 0.75,
    "disaster": 0.85, "catastrophe": 0.85, "catastrophic": 0.85,
    "bloodbath": 0.9, "panic": 0.75, "panic selling": 0.85,
    "bearish": 0.75, "bust": 0.75, "recession": 0.7, "depression": 0.8,
    "bankrupt": 0.9, "bankruptcy": 0.9, "default": 0.8, "insolvent": 0.85,
    "liquidation": 0.85, "meltdown": 0.85,
    # Medium negative (0.4-0.69)
    "fall": 0.55, "falls": 0.55, "falling": 0.55, "fell": 0.55,
    "drop": 0.55, "drops": 0.55, "dropped": 0.55, "dropping": 0.55,
    "decline": 0.55, "declines": 0.55, "declined": 0.55, "declining": 0.55,
    "slump": 0.6, "slumps": 0.6, "slumped": 0.6, "tumble": 0.6,
    "tumbles": 0.6, "tumbled": 0.6, "dip": 0.4, "dips": 0.4,
    "loss": 0.5, "losses": 0.5, "losing": 0.5, "lost": 0.5,
    "weakness": 0.5, "weak": 0.5, "weakening": 0.5, "vulnerable": 0.5,
    "negative": 0.5, "pessimism": 0.5, "pessimistic": 0.5,
    "downgrade to sell": 0.7, "sell rating": 0.6, "strong sell": 0.7,
    "fear": 0.55, "concerns": 0.5, "worries": 0.5, "warning": 0.5,
    "risk": 0.4, "risky": 0.4, "volatile": 0.45, "volatility": 0.4,
    # Mild negative (0.2-0.39)
    "flat": 0.2, "unchanged": 0.2, "sideways": 0.2, "stagnant": 0.25,
    "slowdown": 0.3, "slowing": 0.3, "cooling": 0.25, "pressure": 0.3,
    "under pressure": 0.35, "below": 0.2, "lower": 0.25, "down": 0.3,
    "cautious": 0.25, "uncertainty": 0.25, "unclear": 0.2,
    "miss estimates": 0.6, "miss forecast": 0.6, "miss expectations": 0.6,
}

# Intensifiers that amplify sentiment
INTENSIFIERS: Dict[str, float] = {
    "very": 1.3, "extremely": 1.5, "significantly": 1.4,
    "substantially": 1.4, "considerably": 1.3, "dramatically": 1.5,
    "sharply": 1.4, "steeply": 1.4, "massively": 1.5,
    "huge": 1.4, "major": 1.3, "majorly": 1.3,
    "heavily": 1.3, "severely": 1.4, "tremendously": 1.5,
}

# Negators that flip sentiment polarity
NEGATORS: set[str] = {
    "not", "no", "never", "neither", "nor", "none",
    "nothing", "nowhere", "hardly", "barely", "scarcely",
    "doesn't", "isn't", "wasn't", "shouldn't", "wouldn't", "couldn't",
    "won't", "don't", "didn't", "can't", "cannot",
    "lack", "lacks", "lacking", "lacked",
    "without", "except", "absence", "absent",
}

# Sample evaluation set (FPB-style taxonomy)
SAMPLE_EVAL_SET: List[Dict[str, str]] = [
    # Positive (10)
    {"text": "Company reports strong Q3 earnings, beating analyst expectations", "label": "positive"},
    {"text": "Stock surges to all-time high on record revenue growth", "label": "positive"},
    {"text": "Firm gets upgraded to buy rating, shares rally", "label": "positive"},
    {"text": "Profit jumps 45% as company gains market share", "label": "positive"},
    {"text": "Strong recovery as revenue rebounds from pandemic lows", "label": "positive"},
    {"text": "Company thrives amid booming demand for products", "label": "positive"},
    {"text": "Analysts bullish as firm crushes earnings estimates", "label": "positive"},
    {"text": "Stock soars on blockbuster earnings report", "label": "positive"},
    {"text": "Record profits as company outperforms peers", "label": "positive"},
    {"text": "Firm reports explosive growth, shares surge", "label": "positive"},
    {"text": "Share price climbs as profits rise", "label": "positive"},
    {"text": "Company gains on positive momentum, improving outlook", "label": "positive"},
    {"text": "Strong sales growth continues, exceeding forecasts", "label": "positive"},
    {"text": "Firm reports upbeat results, stock jumps", "label": "positive"},
    {"text": "Business thrives with rising revenue and profit", "label": "positive"},
    # Negative (10)
    {"text": "Company misses earnings, shares crash on recession fears", "label": "negative"},
    {"text": "Stock plunges to record low after disappointing guidance", "label": "negative"},
    {"text": "Firm gets downgraded to sell, shares tumble", "label": "negative"},
    {"text": "Losses mount as company struggles with weak demand", "label": "negative"},
    {"text": "Declining revenue and falling profit raise concerns", "label": "negative"},
    {"text": "Stock collapses amid panic selling, bears take control", "label": "negative"},
    {"text": "Company warns of bankruptcy risk, shares plummet", "label": "negative"},
    {"text": "Massive losses as firm defaults on debt", "label": "negative"},
    {"text": "Catastrophic quarter as revenue drops sharply", "label": "negative"},
    {"text": "Bloodbath in shares after shocking profit warning", "label": "negative"},
    {"text": "Share price drops as losses widen", "label": "negative"},
    {"text": "Company slides amid weak sales, pessimism grows", "label": "negative"},
    {"text": "Firm tumbles on fears of recession", "label": "negative"},
    {"text": "Revenue falls short, stock slumps", "label": "negative"},
    {"text": "Business declines amid negative outlook", "label": "negative"},
    # Neutral (10)
    {"text": "Company reports in-line earnings", "label": "neutral"},
    {"text": "Stock holds steady amid mixed signals", "label": "neutral"},
    {"text": "Firm maintains current guidance, shares unchanged", "label": "neutral"},
    {"text": "Revenue flat year-over-year, profit unchanged", "label": "neutral"},
    {"text": "Stock trades sideways in narrow range", "label": "neutral"},
    {"text": "Company issues statement without material updates", "label": "neutral"},
    {"text": "Share price remains stable on low volume", "label": "neutral"},
    {"text": "Firm holds annual meeting, no announcements", "label": "neutral"},
    {"text": "Business as usual amid steady performance", "label": "neutral"},
    {"text": "Company provides update without revenue figures", "label": "neutral"},
    {"text": "Stock unchanged as market digests news", "label": "neutral"},
    {"text": "Firm reports steady results in line with forecasts", "label": "neutral"},
    {"text": "No material change in outlook", "label": "neutral"},
    {"text": "Company maintains current position", "label": "neutral"},
    {"text": "Business operates as expected without surprises", "label": "neutral"},
]


def _tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase words."""
    return text.lower().split()


def _count_sentiment_words(tokens: List[str], lexicon: Dict[str, float]) -> List[Tuple[str, float]]:
    """Find sentiment words in token list and return their weights."""
    hits = []
    for token in tokens:
        if token in lexicon:
            hits.append((token, lexicon[token]))
    return hits


def _detect_negation(tokens: List[str]) -> bool:
    """Check if any negator appears before sentiment words."""
    return any(token in NEGATORS for token in tokens)


def _get_intensifier_multiplier(tokens: List[str]) -> float:
    """Calculate intensifier multiplier from tokens."""
    multiplier = 1.0
    for token in tokens:
        if token in INTENSIFIERS:
            multiplier = max(multiplier, INTENSIFIERS[token])
    return min(multiplier, 2.0)  # Cap at 2x


def score_sentiment(text: str) -> Dict[str, object]:
    """Score financial text sentiment.

    Args:
        text: Financial text to analyze.

    Returns:
        Dictionary with:
            - score: float in [-1.0, 1.0]
            - label: "positive" | "negative" | "neutral"
            - confidence: float in [0.0, 1.0]
            - positive_hits: list of (term, weight) tuples
            - negative_hits: list of (term, weight) tuples
            - negated: bool
    """
    if not text or not text.strip():
        return {
            "score": 0.0,
            "label": "neutral",
            "confidence": 0.0,
            "positive_hits": [],
            "negative_hits": [],
            "negated": False,
        }

    tokens = _tokenize(text)

    # Detect negation
    negated = _detect_negation(tokens)

    # Get intensifier multiplier
    intensifier = _get_intensifier_multiplier(tokens)

    # Find sentiment words
    pos_hits = _count_sentiment_words(tokens, POSITIVE_LEXICON)
    neg_hits = _count_sentiment_words(tokens, NEGATIVE_LEXICON)

    # Calculate raw score
    pos_score = sum(w for _, w in pos_hits) if pos_hits else 0.0
    neg_score = sum(w for _, w in neg_hits) if neg_hits else 0.0

    # Apply intensifier
    pos_score *= intensifier
    neg_score *= intensifier

    # Apply negation (flip polarity)
    if negated:
        pos_score, neg_score = neg_score, pos_score

    # Net score
    raw_score = pos_score - neg_score

    # Normalize to [-1, 1] using tanh-like compression
    import math
    if raw_score > 0:
        score = 1.0 - math.exp(-raw_score)
    elif raw_score < 0:
        score = -1.0 + math.exp(raw_score)
    else:
        score = 0.0

    # Clamp
    score = max(-1.0, min(1.0, score))

    # Determine label
    if score > 0.1:
        label = "positive"
    elif score < -0.1:
        label = "negative"
    else:
        label = "neutral"

    # Confidence based on total sentiment weight
    total_weight = pos_score + neg_score
    confidence = min(1.0, total_weight / 3.0)  # Normalize: 3+ weight = max confidence

    return {
        "score": round(score, 4),
        "label": label,
        "confidence": round(confidence, 4),
        "positive_hits": pos_hits,
        "negative_hits": neg_hits,
        "negated": negated,
    }


def score_batch(texts: List[str]) -> List[Dict[str, object]]:
    """Score multiple texts for sentiment.

    Args:
        texts: List of financial texts to analyze.

    Returns:
        List of sentiment dictionaries.
    """
    return [score_sentiment(text) for text in texts]


def map_sentiment_to_signal(
    score: float,
    threshold_pos: float = 0.2,
    threshold_neg: float = -0.2,
) -> Dict[str, object]:
    """Map sentiment score to trading signal.

    Args:
        score: Sentiment score in [-1.0, 1.0].
        threshold_pos: Score above which → LONG.
        threshold_neg: Score below which → FLAT.

    Returns:
        Dictionary with:
            - signal: "LONG" | "FLAT"
            - confidence: float in [0.0, 1.0]
            - reason: human-readable reason
    """
    if score > threshold_pos:
        confidence = min(1.0, (score - threshold_pos) / (1.0 - threshold_pos))
        return {
            "signal": "LONG",
            "confidence": round(confidence, 4),
            "reason": f"Sentiment score {score:.3f} > {threshold_pos} threshold",
        }
    elif score < threshold_neg:
        confidence = min(1.0, (threshold_neg - score) / (threshold_neg + 1.0))
        return {
            "signal": "FLAT",
            "confidence": round(confidence, 4),
            "reason": f"Sentiment score {score:.3f} < {threshold_neg} threshold",
        }
    else:
        return {
            "signal": "FLAT",
            "confidence": 0.3,
            "reason": f"Sentiment score {score:.3f} within neutral band",
        }


def generate_synthetic_sentiment(
    returns: List[float],
    lookback: int = 5,
    noise_std: float = 0.1,
) -> List[float]:
    """Generate synthetic sentiment from returns (for backtesting only).

    WARNING: This is synthetic sentiment. Any backtest results are FRAUDULENT
    for alpha claims. This demonstrates overlay mechanics only.

    Args:
        returns: List of daily returns.
        lookback: Number of days to look back for sentiment.
        noise_std: Standard deviation of noise.

    Returns:
        List of sentiment scores in [-1.0, 1.0].
    """
    import math
    import random

    sentiments = []
    for i in range(len(returns)):
        # Look back N days
        start = max(0, i - lookback + 1)
        window = returns[start:i + 1]
        avg_return = sum(window) / len(window)

        # Convert return to sentiment using tanh
        raw = math.tanh(avg_return * 10)  # Scale factor

        # Add noise
        noise = random.gauss(0, noise_std)
        sentiment = raw + noise

        # Clamp
        sentiment = max(-1.0, min(1.0, sentiment))
        sentiments.append(sentiment)

    return sentiments


def run_evaluation() -> Dict[str, object]:
    """Run evaluation on sample set.

    Returns:
        Dictionary with:
            - accuracy: float in [0.0, 1.0]
            - macro_f1: float in [0.0, 1.0]
            - confusion: dict with confusion matrix
            - per_label: dict with per-label metrics
    """
    # Run batch scoring
    texts = [s["text"] for s in SAMPLE_EVAL_SET]
    true_labels = [s["label"] for s in SAMPLE_EVAL_SET]
    pred_results = score_batch(texts)
    pred_labels = [r["label"] for r in pred_results]

    # Confusion matrix
    confusion = {"true_pos": 0, "true_neg": 0, "false_pos": 0, "false_neg": 0}
    for true, pred in zip(true_labels, pred_labels):
        if true == "positive" and pred == "positive":
            confusion["true_pos"] += 1
        elif true == "negative" and pred == "negative":
            confusion["true_neg"] += 1
        elif true != pred:
            if pred == "positive":
                confusion["false_pos"] += 1
            else:
                confusion["false_neg"] += 1

    # Per-label metrics
    labels = ["positive", "negative", "neutral"]
    per_label = {}
    for label in labels:
        tp = sum(1 for t, p in zip(true_labels, pred_labels) if t == label and p == label)
        fp = sum(1 for t, p in zip(true_labels, pred_labels) if t != label and p == label)
        fn = sum(1 for t, p in zip(true_labels, pred_labels) if t == label and p != label)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        per_label[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": sum(1 for t in true_labels if t == label),
        }

    # Accuracy
    correct = sum(1 for t, p in zip(true_labels, pred_labels) if t == p)
    accuracy = correct / len(true_labels)

    # Macro F1
    macro_f1 = sum(m["f1"] for m in per_label.values()) / len(labels)

    return {
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "confusion": confusion,
        "per_label": per_label,
        "total": len(true_labels),
    }
