import logging
import os
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

class FredMacroProvider:
    """
    Fetches select macro indicators from FRED (e.g., T10Y2Y spread, T10YIE inflation expectation)
    to classify macroeconomic regimes for dynamic risk scaling.
    """
    def __init__(self):
        # Base FRED endpoints (series_id) using St. Louis Fed API if key provided,
        # or simple web scraping / alternate proxy if keyless.
        # We will use the FRED Observations API. Requires API key usually.
        # But we can also fetch from fred.stlouisfed.org HTML directly,
        # or we just rely on the API and degrade to NEUTRAL on 403 (Missing Key).
        self.api_key = os.environ.get("FRED_API_KEY", "")
        self.base_url = "https://api.stlouisfed.org/fred/series/observations"

    def _fetch_series(self, series_id: str) -> float:
        """
        Fetches the latest value for a given FRED series ID.
        Retries up to 3 times on 429/5xx, with 5s timeout.
        Returns None on any unrecoverable failure.
        """
        if not self.api_key:
            logger.warning(f"FRED_API_KEY is empty. Failing closed for {series_id}.")
            return None

        url = f"{self.base_url}?series_id={series_id}&api_key={self.api_key}&file_type=json&sort_order=desc&limit=1"

        max_retries = 3
        base_delay = 1.0

        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=5.0)

                if response.status_code == 200:
                    data = response.json()
                    observations = data.get("observations", [])
                    if observations:
                        val_str = observations[0].get("value", ".")
                        if val_str != ".":
                            return float(val_str)
                    # If we reach here, it was a 200 OK but data was missing/invalid
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"FRED API returned empty data for {series_id}. Retrying in {delay}s...")
                    time.sleep(delay)
                elif response.status_code in (429, 500, 502, 503, 504):
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"FRED API {response.status_code} for {series_id}. Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.warning(f"FRED API failed with status {response.status_code} for {series_id}.")
                    return None

            except requests.exceptions.RequestException as e:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Network error fetching {series_id}: {e}. Retrying in {delay}s...")
                time.sleep(delay)
            except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
                logger.error(f"Unexpected error fetching {series_id}: {e}")
                return None

        return None

    def get_regime(self) -> dict[str, Any]:
        """
        Classifies the current regime based on T10Y2Y (term spread) and T10YIE (inflation).
        Falls back to NEUTRAL if data is unavailable.
        """
        # T10Y2Y: 10-Year Treasury Constant Maturity Minus 2-Year Treasury Constant Maturity
        # T10YIE: 10-Year Breakeven Inflation Rate
        term_spread = self._fetch_series("T10Y2Y")
        inflation = self._fetch_series("T10YIE")

        if term_spread is None or inflation is None:
            logger.warning("Could not fetch required FRED macro data. Defaulting to NEUTRAL regime.")
            return {
                "regime": "NEUTRAL",
                "confidence": 0.0,
                "term_spread": None,
                "inflation": None
            }

        # Basic heuristic classification
        # Inversion (spread < 0) often signals recession risk (RISK-OFF)
        # High inflation (> 2.5%) combined with inversion or low growth = STAGFLATION
        # Normal (spread > 0) + moderate inflation = RISK-ON

        regime = "NEUTRAL"
        confidence = 0.5

        if term_spread < 0:
            if inflation > 2.5:
                regime = "STAGFLATION"
                confidence = 0.8
            else:
                regime = "RISK_OFF"
                confidence = 0.7
        else:
            if inflation < 2.5:
                regime = "RISK_ON"
                confidence = 0.6
            elif inflation >= 2.5:
                # Growth with inflation
                regime = "NEUTRAL"
                confidence = 0.4

        return {
            "regime": regime,
            "confidence": confidence,
            "term_spread": term_spread,
            "inflation": inflation
        }

    def regime_multiplier(self) -> float:
        """
        Returns a position sizing scale factor based on the current macro regime.
        """
        regime_data = self.get_regime()
        regime = regime_data["regime"]

        if regime == "RISK_ON":
            return 1.0
        elif regime == "NEUTRAL":
            return 0.8
        elif regime == "RISK_OFF":
            return 0.5
        elif regime == "STAGFLATION":
            return 0.4

        return 0.8 # Fallback default

    def get_historical_regimes(self) -> dict[str, str]:
        """
        Fetches full historical daily series from public keyless FRED links,
        aligns them, and returns a dictionary of 'YYYY-MM-DD' -> regime label.
        """
        try:
            import pandas as pd
            spread_df = pd.read_csv("https://fred.stlouisfed.org/graph/fredgraph.csv?id=T10Y2Y")
            spread_df.columns = ["Date", "Spread"]
            spread_df["Date"] = pd.to_datetime(spread_df["Date"])
            spread_df["Spread"] = pd.to_numeric(spread_df["Spread"], errors="coerce")
            spread_df = spread_df.dropna()

            inf_df = pd.read_csv("https://fred.stlouisfed.org/graph/fredgraph.csv?id=T10YIE")
            inf_df.columns = ["Date", "Inflation"]
            inf_df["Date"] = pd.to_datetime(inf_df["Date"])
            inf_df["Inflation"] = pd.to_numeric(inf_df["Inflation"], errors="coerce")
            inf_df = inf_df.dropna()

            merged = pd.merge(spread_df, inf_df, on="Date", how="inner")
            regimes = {}
            for _, row in merged.iterrows():
                dt_str = row["Date"].strftime("%Y-%m-%d")
                spread = row["Spread"]
                inflation = row["Inflation"]

                if spread < 0:
                    if inflation > 2.5:
                        regime = "STAGFLATION"
                    else:
                        regime = "RISK_OFF"
                else:
                    if inflation < 2.5:
                        regime = "RISK_ON"
                    else:
                        regime = "NEUTRAL"
                regimes[dt_str] = regime
            return regimes
        except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
            logger.warning(f"Failed to fetch historical FRED data: {e}. Defaulting to NEUTRAL regimes.")
            return {}
