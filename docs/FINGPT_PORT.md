# FinGPT Sentiment Factor Port

## Overview

This module ports the sentiment analysis approach from FinGPT into a lexicon-based financial sentiment scorer for the WSB-Alpha-System. The original FinGPT uses LLM-based models; this port replaces that with a rule-based lexicon scorer that runs offline with no API keys or model downloads.

## Architecture Mapping

| FinGPT Component | WSB-Alpha Port | Notes |
|---|---|---|
| LLM-based sentiment model | Lexicon-based scorer (`score_sentiment()`) | Rule-based, no model download |
| Training data / fine-tuning | Finance-specific lexicons (POSITIVE/NEGATIVE) | 100+ terms each, hand-weighted |
| Tokenization | Simple whitespace split (`_tokenize()`) | Lowercase, no subword |
| Sentiment prediction | Weighted sum + tanh normalization | Score in [-1, 1] |
| Positive/negative labels | 3-class: positive/negative/neutral | Threshold: ±0.1 |
| Confidence calibration | Weight-based confidence | Total weight / 3.0, capped at 1.0 |
| Factor mapping | `map_sentiment_to_signal()` | >0.2 → LONG, <-0.2 → FLAT |

## Lexicon Design

### POSITIVE_LEXICON (100+ terms)
- **Strong (0.7–1.0):** surge, rally, soar, breakout, record high, upgrade, outperform, beat, blowout, bullish, moon, thrash, crush
- **Medium (0.4–0.69):** rise, gain, jump, spike, recovery, rebound, growth, profit, dividend, upside, strong, positive
- **Mild (0.2–0.39):** stable, steady, improve, support, up, higher, above

### NEGATIVE_LEXICON (100+ terms)
- **Strong (0.7–1.0):** crash, plunge, record low, downgrade, underperform, miss, bankruptcy, bloodbath, panic, recession
- **Medium (0.4–0.69):** fall, drop, decline, slump, tumble, loss, weakness, fear, concern, risk, volatile
- **Mild (0.2–0.39):** flat, unchanged, sideways, slowdown, pressure, below, lower, cautious

### Modifiers
- **INTENSIFIERS (15 terms):** very (1.3×), extremely (1.5×), significantly (1.4×), dramatically (1.5×), sharply (1.4×), etc. Multiplier capped at 2.0×.
- **NEGATORS (30+ terms):** not, no, never, don't, can't, won't, lack, without, absence, etc. Flips polarity of all sentiment words.

## Signal Mapping

| Score Range | Signal | Confidence |
|---|---|---|
| > 0.2 | LONG | Scaled from 0 to 1.0 based on distance from threshold |
| < -0.2 | FLAT | Scaled from 0 to 1.0 based on distance from threshold |
| [-0.2, 0.2] | FLAT | Fixed 0.3 (neutral band) |

## NOT Ported (FinGPT Components Omitted)

| Component | Reason |
|---|---|
| LLM model (Llama-2, Bloom, etc.) | Requires GPU, model downloads, API keys |
| Training pipeline | No training data or compute budget |
| RLHF / fine-tuning | Requires human feedback loop |
| Multi-turn prompting | Rule-based scorer has no conversation state |
| Real-time news ingestion | Offline-only constraint |
| Social media scraping | No network access |
| Sentiment ensemble (multiple models) | Single lexicon-based scorer |
| Model inference optimization | No model to optimize |

## Evaluation

### Evaluation Set
- **Size:** 45 sentences (15 positive, 15 negative, 15 neutral)
- **Style:** FPB-style taxonomy with financial earnings/stock movement sentences
- **Location:** `src/signals/fingpt_sentiment.py::SAMPLE_EVAL_SET`

### Running Evaluation
```bash
# Quick evaluation
PYTHONPATH=. python scripts/fingpt_eval.py

# Full report with backtest overlay
PYTHONPATH=. python scripts/fingpt_eval.py --backtest
```

### Verification Numbers

| Metric | Value |
|---|---|
| Accuracy | 80.00% |
| Macro F1 | 0.7872 |
| Positive Precision | 0.7647 |
| Positive Recall | 0.8667 |
| Negative Precision | 0.8333 |
| Negative Recall | 1.0000 |
| Neutral Precision | 0.8000 |
| Neutral Recall | 0.5333 |

**Confusion Matrix:** TP=13, TN=15, FP=4, FN=5

### Test Suite
- **Location:** `tests/test_fingpt_port.py`
- **Test Count:** 33 tests across 10 test classes
- **Run:** `PYTHONPATH=. pytest tests/test_fingpt_port.py -v`

#### Test Classes
1. `TestLexicons` — Lexicon integrity, no overlaps, weights in range
2. `TestScoreSentiment` — Core scoring, bounds, label assignment
3. `TestNegation` — Negator detection and polarity flip
4. `TestIntensifiers` — Multiplier application and capping
5. `TestMapSentimentToSignal` — Signal mapping, thresholds, neutral band
6. `TestScoreBatch` — Batch scoring consistency
7. `TestEvaluationHarness` — `run_evaluation()` returns valid metrics
8. `TestSampleEvalSet` — Eval set integrity (15/15/15 split)
9. `TestEdgeCases` — Empty strings, whitespace, special characters
10. `TestPerformance` — Batch scoring within time bounds

## Files Created

| File | Purpose |
|---|---|
| `src/signals/fingpt_sentiment.py` | Lexicon scorer + factor mapping (425 lines) |
| `tests/test_fingpt_port.py` | Test suite (33 tests) |
| `scripts/fingpt_eval.py` | CLI eval + optional backtest |
| `docs/FINGPT_PORT.md` | This document |

## Usage

```python
from src.signals.fingpt_sentiment import score_sentiment, map_sentiment_to_signal

# Score a financial headline
result = score_sentiment("Company beats earnings, stock surges")
print(result["score"])    # 0.6132
print(result["label"])    # "positive"
print(result["confidence"])  # 0.5

# Map to trading signal
signal = map_sentiment_to_signal(result["score"])
print(signal["signal"])   # "LONG"
print(signal["confidence"])  # 0.7665

# Negation handling
result = score_sentiment("Company does not beat earnings")
print(result["score"])    # Negative (negated positive → negative)
print(result["negated"])  # True

# Intensifier handling
result = score_sentiment("Company extremely bullish on outlook")
print(result["score"])    # Higher than without "extremely"
```

## Constraints

- **Offline only:** No API keys, network calls, or model downloads
- **Alpaca stocks only:** Factor mapping applies to SPY timing overlay
- **Paper only:** No real money deployment
- **No lookahead:** Evaluation uses only past data
- **Registry untouched:** `strategies/registry.json` is never modified
- **Synthetic backtest disclaimer:** Backtest results using synthetic sentiment are demonstrative only, NOT alpha claims
