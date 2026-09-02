import pandas as pd
from typing import Dict, Any

from src.alpha.h1_features import compute_regime_features
from src.alpha.h1_hmm import RegimeHMM
from src.alpha.h1_regime_filter import RegimeFilter

class RegimeDetector:
    """
    Wraps RegimeHMM and RegimeFilter to detect regimes and apply rules
    end-to-end for the meta-strategy.
    """
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        n_components = self.config.get("n_states", 4)

        self.hmm = RegimeHMM(n_components=n_components)
        self.filter = RegimeFilter()

    def train(self, df: pd.DataFrame):
        """Trains the underlying HMM on the historical dataframe."""
        normalization = self.config.get("normalization", "zscore")
        features = compute_regime_features(df, normalization=normalization)
        self.hmm.fit(features)

    def detect_regime(self, df: pd.DataFrame) -> pd.Series:
        """
        Computes features and predicts the regime for the given DataFrame.
        Returns a Series of string regime labels.
        """
        normalization = self.config.get("normalization", "zscore")
        features = compute_regime_features(df, normalization=normalization)

        if not self.hmm.is_fitted:
            # Auto-fit if not already fitted, typically useful for walk-forward or
            # if we just want to apply it immediately on historical data
            self.hmm.fit(features)

        numeric_states = self.hmm.predict(features)

        # Convert numeric states to string labels via mapping in config or default
        label_map = self.config.get("regime_labels", self.hmm.label_map)

        # Apply the mapping
        string_labels = numeric_states.map(label_map)
        return string_labels

    def apply_regime_filter(self, df: pd.DataFrame, signals: pd.DataFrame) -> pd.DataFrame:
        """
        Applies regime filtering to an existing signals dataframe using
        features derived from the price dataframe `df`.
        """
        # Ensure indices match
        if not df.index.equals(signals.index):
            # Attempt to align
            signals = signals.reindex(df.index)

        regime_labels = self.detect_regime(df)

        regime_rules = self.config.get("regime_config", {})

        filtered_signals = self.filter.filter_signals(signals, regime_labels, regime_rules)
        return filtered_signals
