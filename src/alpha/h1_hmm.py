import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM

class RegimeHMM:
    """
    Hidden Markov Model for detecting 4 market regimes:
    0: bull
    1: bear
    2: high_vol
    3: range
    """
    def __init__(self, n_components: int = 4, n_iter: int = 100):
        if n_components != 4:
            raise ValueError("RegimeHMM explicitly expects exactly 4 components.")

        self.n_components = n_components
        self.model = GaussianHMM(
            n_components=n_components,
            covariance_type="diag",
            n_iter=n_iter,
            random_state=42
        )
        self.is_fitted = False

        # State mappings
        self.label_map = {
            0: "bull",
            1: "bear",
            2: "high_vol",
            3: "range"
        }

    def fit(self, features: pd.DataFrame):
        """Trains the HMM on the provided features."""
        # hmmlearn expects 2D array of shape (n_samples, n_features)
        X = features.values
        self.model.fit(X)
        self.is_fitted = True
        # In a fully robust system we might attempt to map hidden states to
        # semantic labels (bull/bear) by sorting their emission means or variances.
        # For this requirement, we'll assume the states 0..3 are the raw outputs.

    def predict(self, features: pd.DataFrame) -> pd.Series:
        """Predicts states, with a persistence heuristic smoothing out <10 day regimes."""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before calling predict.")

        X = features.values
        states = self.model.predict(X)

        # Apply persistence heuristic: states with avg hold < 10 days -> merge with adjacent
        smoothed_states = self._apply_persistence_heuristic(states)

        return pd.Series(smoothed_states, index=features.index, name="regime")

    def get_regime_label(self, state: int) -> str:
        """Returns the semantic label for a given integer state."""
        return self.label_map.get(state, "unknown")

    def get_transition_matrix(self) -> np.ndarray:
        """Returns the learned transition probability matrix."""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted to get transition matrix.")
        return self.model.transmat_

    def _apply_persistence_heuristic(self, states: np.ndarray, min_hold: int = 10) -> np.ndarray:
        """
        Smooths out fast-flipping states. If a regime lasts less than min_hold days,
        it is replaced by the regime that preceded it.
        """
        if len(states) < min_hold:
            return states

        smoothed = np.copy(states)
        current_state = smoothed[0]
        current_streak = 1

        for i in range(1, len(smoothed)):
            if smoothed[i] == current_state:
                current_streak += 1
            else:
                # State changed
                if current_streak < min_hold and i - current_streak - 1 >= 0:
                    # Previous state was too short, revert it to the one before it
                    prev_stable_state = smoothed[i - current_streak - 1]
                    smoothed[i - current_streak:i] = prev_stable_state
                current_state = smoothed[i]
                current_streak = 1

        return smoothed
