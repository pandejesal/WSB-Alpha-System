
import pandas as pd

from src.ops.signals import (
    get_btc_vol_target_sma100_signal,
    get_spy_rsi2_signal,
    get_spy_sma200_signal,
    get_us_momentum_top5_signal,
)

from .schemas import SignalsReport, SleeveSignal


class SignalEngine:
    def __init__(self):
        self.active_sleeves = [
            "us_momentum_top5",
            "spy_sma200",
            "spy_rsi2",
            "btc_vol_target_sma100",
            "us_lowvol_top30",
            "us_pead_top5",
            "breakout_burst"
        ]

    def _generate_momentum_top5(self, date: pd.Timestamp, data: dict[str, pd.DataFrame]) -> SleeveSignal:
        if not data:
            return SleeveSignal(id="us_momentum_top5", signal="FLAT", confidence=0.0, params={"warning": "data_unavailable"})

        frames = []
        tickers = []
        for ticker, df in data.items():
            if df is not None and not df.empty and 'Close' in df.columns:
                # We need to construct a multi-index dataframe mimicking yfinance download output
                df_close = df[['Close']].copy()
                df_close.columns = pd.MultiIndex.from_product([['Close'], [ticker]])
                frames.append(df_close)
                tickers.append(ticker)

        if not frames:
            return SleeveSignal(id="us_momentum_top5", signal="FLAT", confidence=0.0, params={"warning": "data_unavailable"})

        combined_df = pd.concat(frames, axis=1)

        sig_data = get_us_momentum_top5_signal(combined_df, tickers)

        if sig_data.get("data_unavailable"):
            return SleeveSignal(id="us_momentum_top5", signal="FLAT", confidence=0.0, params={"warning": "data_unavailable"})

        # The logic is rank-based. Signals are always LONG for the top 5
        return SleeveSignal(
            id="us_momentum_top5",
            signal="LONG",
            confidence=1.0,
            params={
                "top_5": sig_data.get("top_5", []),
                "momenta": sig_data.get("momenta", {})
            }
        )

    def _generate_spy_sma200(self, date: pd.Timestamp, data: dict[str, pd.DataFrame]) -> SleeveSignal:
        spy_data = data.get("SPY")
        if spy_data is None or spy_data.empty:
            return SleeveSignal(id="spy_sma200", signal="FLAT", confidence=0.0, params={"warning": "data_unavailable"})

        sig_data = get_spy_sma200_signal(spy_data)
        if sig_data.get("data_unavailable"):
            return SleeveSignal(id="spy_sma200", signal="FLAT", confidence=0.0, params={"warning": "data_unavailable"})

        raw_signal = sig_data.get("signal", "CASH")
        signal_mapped = "LONG" if raw_signal == "BUY" else "FLAT"

        return SleeveSignal(
            id="spy_sma200",
            signal=signal_mapped,
            confidence=1.0,
            params={
                "sma200": sig_data.get("sma200"),
                "last_close": sig_data.get("last_close")
            }
        )

    def _generate_spy_rsi2(self, date: pd.Timestamp, data: dict[str, pd.DataFrame]) -> SleeveSignal:
        spy_data = data.get("SPY")
        if spy_data is None or spy_data.empty:
            return SleeveSignal(id="spy_rsi2", signal="FLAT", confidence=0.0, params={"warning": "data_unavailable"})

        sig_data = get_spy_rsi2_signal(spy_data)
        if sig_data.get("data_unavailable"):
            return SleeveSignal(id="spy_rsi2", signal="FLAT", confidence=0.0, params={"warning": "data_unavailable"})

        rsi2 = sig_data.get("rsi2")
        sma5 = sig_data.get("sma5")
        last_close = sig_data.get("last_close")

        signal = "FLAT"
        if rsi2 is not None and rsi2 < 10:
            signal = "LONG"
        elif rsi2 is not None and rsi2 > 70 or last_close is not None and sma5 is not None and last_close > sma5:
            signal = "FLAT"
        else:
            signal = "HOLD"

        return SleeveSignal(
            id="spy_rsi2",
            signal=signal,
            confidence=1.0,
            params={
                "rsi2": rsi2,
                "sma5": sma5,
                "last_close": last_close
            }
        )

    def _generate_btc_vol_target(self, date: pd.Timestamp, data: dict[str, pd.DataFrame]) -> SleeveSignal:
        btc_data = data.get("BTC-USD")
        if btc_data is None or btc_data.empty:
            return SleeveSignal(id="btc_vol_target_sma100", signal="FLAT", confidence=0.0, params={"warning": "data_unavailable"})

        sig_data = get_btc_vol_target_sma100_signal(btc_data)
        if sig_data.get("data_unavailable"):
            return SleeveSignal(id="btc_vol_target_sma100", signal="FLAT", confidence=0.0, params={"warning": "data_unavailable"})

        target_exposure = sig_data.get("target_exposure", 0.0)
        signal = "LONG" if target_exposure > 0 else "FLAT"

        return SleeveSignal(
            id="btc_vol_target_sma100",
            signal=signal,
            confidence=1.0 if target_exposure > 0 else 0.0,
            params={
                "realized_vol": sig_data.get("realized_vol"),
                "sma100": sig_data.get("sma100"),
                "last_close": sig_data.get("last_close"),
                "target_exposure": target_exposure
            }
        )

    def generate_all_signals(self, run_id: str, date: str, mode: str, market_data: dict[str, pd.DataFrame]) -> SignalsReport:
        sleeves = []

        dt = pd.to_datetime(date)

        for sleeve_id in self.active_sleeves:
            if sleeve_id == "us_momentum_top5":
                sleeves.append(self._generate_momentum_top5(dt, market_data))
            elif sleeve_id == "spy_sma200":
                sleeves.append(self._generate_spy_sma200(dt, market_data))
            elif sleeve_id == "spy_rsi2":
                sleeves.append(self._generate_spy_rsi2(dt, market_data))
            elif sleeve_id == "btc_vol_target_sma100":
                sleeves.append(self._generate_btc_vol_target(dt, market_data))
            else:
                sleeves.append(SleeveSignal(
                    id=sleeve_id,
                    signal="FLAT",
                    confidence=0.0,
                    params={"warning": "pending P4 port"}
                ))

        return SignalsReport(
            run_id=run_id,
            date=date,
            mode=mode,
            sleeves=sleeves
        )

def run_signals(run_id: str, date: str, mode: str, market_data: dict[str, pd.DataFrame]) -> SignalsReport:
    engine = SignalEngine()
    return engine.generate_all_signals(run_id, date, mode, market_data)
