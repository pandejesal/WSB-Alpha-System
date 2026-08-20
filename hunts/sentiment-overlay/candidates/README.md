# Sentiment Overlay Candidates

## Candidate 1: `sentiment_overlay_sma_entry_v1`
- **Overlay Design:** Uses the debate engine's consensus score as an entry filter on the base `spy_sma200` strategy.
- **Threshold Rationale:** `score > 0.0` ensures we only enter bullish trends when market news sentiment is also positive.
- **Data Availability:** If sentiment data is unavailable, it gracefully falls back to the un-overlayed `spy_sma200` signal.
- **Invalidation:** Fails if the overlay reduces the number of trades below 10 or fails to provide a >0.1 Sharpe ratio lift.

## Candidate 2: `sentiment_overlay_momentum_veto_v1`
- **Overlay Design:** Uses the debate engine's consensus score as a risk-off veto for the base `us_momentum_top5` strategy.
- **Threshold Rationale:** `score < -0.2` triggers a veto, preventing entry into momentum stocks when broader sentiment is significantly bearish.
- **Data Availability:** If sentiment data is unavailable, it gracefully falls back to the standard momentum entry.
- **Invalidation:** Fails if the veto condition rarely triggers or if it fails to improve the risk-adjusted returns (Sharpe lift > 0.1) without cutting trades drastically.