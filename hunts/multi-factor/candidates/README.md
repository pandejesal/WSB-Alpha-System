# Multi-Factor Candidate Strategies

This directory contains three candidate strategy specifications for the `multi_factor` hunt session.

## 1. multi_factor_canslim_lite_v1 (CANSLIM-lite 6-factor)

-   **Factor Set:** Current Earnings (C), Annual Earnings (A), New High (N), Strong Sector (S), Institutional Support (I), Market Direction (M).
-   **Scoring Rule:** >= 4 out of 6 factors must be met, combined with market breadth >= 60 and FRED macro regime `!= BEAR`.
-   **Data Availability:**
    -   Price/volume/market direction (SPY) exist in the current yfinance/indicator pipeline.
    -   Earnings growth, sector relative strength, and institutional ownership require new fundamentals plumbing (e.g., integrating Tiingo/FMP API).
-   **Invalidation:** Fails if the new fundamental endpoints cannot provide accurate daily snapshot data without lookahead bias, or if >40% of the universe is missing required fundamental data.

## 2. multi_factor_vcp_breadth_v1 (VCP-style with breadth gate)

-   **Factor Set:** Volatility Contraction Pattern (VCP), Market Breadth (percentage above 50-day SMA), Volume Dry-up.
-   **Scoring Rule:** VCP base with >= 2 contractions and < 25% max drawdown, intersecting with market breadth >= 60% and volume dry-up (< 50% of 50d avg).
-   **Data Availability:**
    -   Fully feasible today using existing daily OHLCV data from yfinance.
    -   Requires new python indicator definitions in `src.alpha.indicators` to compute VCP contractions and breadth efficiently.
-   **Invalidation:** Fails if the VCP pattern recognition logic yields too few trading opportunities (starvation) or if breadth filter introduces a lag that degrades entry performance.

## 3. multi_factor_earnings_mom_v1 (Earnings Momentum + Regime Filter)

-   **Factor Set:** Earnings Surprise, Price Momentum (3-month return), FRED Macro Regime.
-   **Scoring Rule:** Positive earnings surprise (> 5%) AND top-quartile price momentum (> 10% 3m return) filtered by FRED Regime (RISK_ON or NEUTRAL).
-   **Data Availability:**
    -   Price momentum and FRED Macro Regime are available in the current pipeline.
    -   Earnings surprise requires new fundamentals plumbing (fetching estimates vs actuals).
-   **Invalidation:** Fails if high-quality earnings estimate data is unavailable historically for the target universe, or if post-earnings announcement drift (PEAD) edge has decayed.
