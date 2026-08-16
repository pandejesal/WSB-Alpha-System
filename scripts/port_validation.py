import os
import json
import yaml
import yfinance as yf
import pandas as pd
import numpy as np

def calculate_rsi(series, period=2):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def compute_signals():
    report = {}

    # Check yfinance data availability for each strategy
    try:
        spy = yf.download("SPY", period="1y", auto_adjust=True, progress=False)
        if spy.empty:
            raise Exception("No SPY data")

        sma200 = spy['Close'].rolling(window=200).mean().iloc[-1].item()
        rsi2 = calculate_rsi(spy['Close'], 2).iloc[-1].item()
        report['spy_sma200'] = {'sma200': sma200, 'close': spy['Close'].iloc[-1].item()}
        report['spy_rsi2'] = {'rsi2': rsi2}
    except Exception as e:
        report['spy_sma200'] = {'data_unavailable': True, 'error': str(e)}
        report['spy_rsi2'] = {'data_unavailable': True, 'error': str(e)}

    try:
        btc = yf.download("BTC-USD", period="1y", auto_adjust=True, progress=False)
        if btc.empty:
            raise Exception("No BTC-USD data")

        returns = btc['Close'].pct_change().dropna()
        realized_vol = (returns.rolling(window=30).std() * np.sqrt(365)).iloc[-1].item()
        sma100 = btc['Close'].rolling(window=100).mean().iloc[-1].item()
        report['btc_vol_target_sma100'] = {'realized_vol': realized_vol, 'sma100': sma100, 'close': btc['Close'].iloc[-1].item()}
    except Exception as e:
        report['btc_vol_target_sma100'] = {'data_unavailable': True, 'error': str(e)}

    try:
        data = yf.download(["SPY", "QQQ"], period="1y", auto_adjust=True, progress=False)['Close']
        if data.empty:
            raise Exception("No SPY/QQQ data")

        spy_close = data['SPY']
        qqq_close = data['QQQ']
        # 1m (21d) momentum skipping 21d
        spy_mom = (spy_close.shift(21) / spy_close.shift(42) - 1).iloc[-1].item()
        qqq_mom = (qqq_close.shift(21) / qqq_close.shift(42) - 1).iloc[-1].item()
        report['dual_momentum'] = {'momentum_SPY': spy_mom, 'momentum_QQQ': qqq_mom}
    except Exception as e:
        report['dual_momentum'] = {'data_unavailable': True, 'error': str(e)}

    try:
        # For top 5 momentum, fetch universe (top 100 names roughly, but we can sample a few to prove concept,
        # or load from config/universe.json)
        with open("config/universe.json", "r") as f:
            universe = json.load(f)["tickers"]

        data = yf.download(universe, period="1y", auto_adjust=True, progress=False)['Close']
        if data.empty:
            raise Exception("No universe data")

        moms = {}
        for ticker in universe:
            if ticker in data.columns:
                series = data[ticker]
                # 6m (126d) momentum skipping 21d
                mom = (series.shift(21) / series.shift(147) - 1).iloc[-1].item()
                if not pd.isna(mom):
                    moms[ticker] = mom

        # top 5
        top_5 = sorted(moms.items(), key=lambda x: x[1], reverse=True)[:5]
        report['us_momentum_top5'] = {'top_5_momentum': top_5}
    except Exception as e:
        report['us_momentum_top5'] = {'data_unavailable': True, 'error': str(e)}

    return report

def validate_schema(spec, expected_keys, strat_id):
    missing_keys = [key for key in expected_keys if key not in spec]
    if missing_keys:
        return False, f"Missing keys in {strat_id}: {missing_keys}"
    return True, "OK"

def main():
    strategies = [
        "us_momentum_top5",
        "spy_sma200",
        "spy_rsi2",
        "btc_vol_target_sma100",
        "dual_momentum"
    ]

    expected_keys = [
        "id", "name", "family", "venue", "universe", "indicators", "parameters",
        "entry_rules", "exit_rules", "position_sizing", "fee_model", "benchmark_result",
        "robustness_notes", "feasibility_at_100", "risks"
    ]

    all_passed = True
    report_data = {}

    for strat_id in strategies:
        try:
            with open(f"strategies/{strat_id}.yaml", "r") as f:
                spec = yaml.safe_load(f)

            passed, msg = validate_schema(spec, expected_keys, strat_id)
            if not passed:
                print(msg)
                all_passed = False

            # Parameter sanity checks
            params = spec.get('parameters', {})
            if strat_id == "us_momentum_top5":
                if params.get('top_n') != 5 or params.get('lookback_days') != 126 or params.get('skip_days') != 21:
                    print(f"Parameter sanity failed for {strat_id}")
                    all_passed = False
            elif strat_id == "spy_sma200":
                if params.get('window') != 200:
                    print(f"Parameter sanity failed for {strat_id}")
                    all_passed = False
            elif strat_id == "spy_rsi2":
                if params.get('entry') != 10 or params.get('exit_rsi') != 70 or params.get('hold_days') != 5:
                    print(f"Parameter sanity failed for {strat_id}")
                    all_passed = False
            elif strat_id == "btc_vol_target_sma100":
                if params.get('target_vol') != 0.30 or params.get('vol_window') != 30 or params.get('gate_window') != 100:
                    print(f"Parameter sanity failed for {strat_id}")
                    all_passed = False
            elif strat_id == "dual_momentum":
                if params.get('lookback_days') != 21 or params.get('skip_days') != 21:
                    print(f"Parameter sanity failed for {strat_id}")
                    all_passed = False

            report_data[strat_id] = {'schema_passed': passed}

        except Exception as e:
            print(f"Error validating {strat_id}: {e}")
            all_passed = False

    try:
        with open("strategies/flagship_portfolio_v1.yaml", "r") as f:
            portfolio_spec = yaml.safe_load(f)

        portfolio_expected_keys = [
            "id", "name", "type", "created", "source", "members", "allocation",
            "fees", "constraints", "expected_metrics", "gates"
        ]

        passed, msg = validate_schema(portfolio_spec, portfolio_expected_keys, "flagship_portfolio_v1")
        if not passed:
            print(msg)
            all_passed = False
        report_data["flagship_portfolio_v1"] = {'schema_passed': passed}

    except Exception as e:
        print(f"Error validating flagship_portfolio_v1: {e}")
        all_passed = False

    signals = compute_signals()
    for k, v in signals.items():
        if k in report_data:
            report_data[k].update(v)

    os.makedirs("docs/data", exist_ok=True)
    with open("docs/data/b1_validation.json", "w") as f:
        json.dump(report_data, f, indent=2)

    if not all_passed:
        exit(1)

if __name__ == "__main__":
    main()
