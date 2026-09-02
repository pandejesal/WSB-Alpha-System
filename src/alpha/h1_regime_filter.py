import pandas as pd

class RegimeFilter:
    """
    Applies regime-specific filters and position sizing multipliers
    to an existing signal DataFrame based on the current regime label.
    """

    def __init__(self):
        pass

    def filter_signals(self, df: pd.DataFrame, regime_labels: pd.Series, regime_config: dict) -> pd.DataFrame:
        """
        Filters signals based on the provided regime configuration.

        Args:
            df: DataFrame containing signals (e.g. 'signal' column with 'long', 'short', 'mean_reversion', 'flat')
            regime_labels: Series of regime labels (strings, e.g. 'bull', 'bear')
            regime_config: dict specifying 'allow_signals' and 'position_multiplier' per regime

        Returns:
            Filtered DataFrame with a new 'regime_context' column and potentially altered signals/sizes.
        """
        # Make a copy to avoid SettingWithCopyWarning
        out = df.copy()

        if "signal" not in out.columns:
            # If there's no signal column, just return with regime context
            out["regime_context"] = regime_labels
            return out

        # Ensure we have a regime context column
        out["regime_context"] = regime_labels

        # Initialize or update size multiplier if applicable
        if "position_multiplier" not in out.columns:
            out["position_multiplier"] = 1.0

        # Iterate over regimes in config
        for regime_name, config in regime_config.items():
            mask = out["regime_context"] == regime_name
            if not mask.any():
                continue

            allowed_signals = config.get("allow_signals", ["long", "short", "mean_reversion"])
            multiplier = config.get("position_multiplier", 1.0)

            # Apply multiplier
            out.loc[mask, "position_multiplier"] *= multiplier

            # Block unallowed signals
            # Any signal not in allowed_signals becomes 'flat' or 0
            if allowed_signals:
                invalid_signal_mask = mask & (~out["signal"].isin(allowed_signals)) & (out["signal"] != "flat")
                out.loc[invalid_signal_mask, "signal"] = "flat"
            else:
                # Empty list means block ALL signals
                out.loc[mask, "signal"] = "flat"

        return out
