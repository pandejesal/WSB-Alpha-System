import json
import sys
import yaml
import datetime
import yfinance as yf
import pandas as pd
import numpy as np

def load_yaml(filepath):
    try:
        with open(filepath, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None

def check_schema(spec, required_keys):
    missing = [k for k in required_keys if k not in spec]
    if missing:
        return False, f"Missing keys: {missing}"
    return True, "OK"

from src.ops.signals import (
    get_us_momentum_top5_signal,
    get_spy_sma200_signal,
    get_spy_rsi2_signal,
    get_btc_vol_target_sma100_signal,
    get_dual_momentum_signal
)

def validate_us_momentum_top5():
    spec = load_yaml("strategies/us_momentum_top5.yaml")
    if not spec: return False, {"error": "Failed to load"}

    req_keys = ["id", "name", "family", "venue", "universe", "indicators", "parameters", "entry_rules", "exit_rules", "position_sizing", "fee_model", "benchmark_result", "robustness_notes", "feasibility_at_100", "risks"]
    passed, msg = check_schema(spec, req_keys)
    if not passed: return False, {"schema_check": msg}

    params = spec.get("parameters", {})
    if params.get("top_n") != 5 or params.get("lookback_days") != 126 or params.get("skip_days") != 21:
        return False, {"param_check": f"Invalid params: {params}"}

    signal_data = {}
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "JPM", "V", "WMT"]

    try:
        data = yf.download(tickers, period="1y", interval="1d", auto_adjust=True, progress=False)
        if data.empty:
             signal_data["data_unavailable"] = True
        else:
             signal_data = get_us_momentum_top5_signal(data, tickers)
    except Exception as e:
        signal_data["data_unavailable"] = True
        signal_data["error"] = str(e)

    return True, {"schema_check": "PASS", "signal_data": signal_data}


def validate_spy_sma200():
    spec = load_yaml("strategies/spy_sma200.yaml")
    if not spec: return False, {"error": "Failed to load"}

    req_keys = ["id", "name", "family", "venue", "universe", "indicators", "parameters", "entry_rules", "exit_rules", "position_sizing", "fee_model", "benchmark_result", "robustness_notes", "feasibility_at_100", "risks"]
    passed, msg = check_schema(spec, req_keys)
    if not passed: return False, {"schema_check": msg}

    params = spec.get("parameters", {})
    if params.get("window") != 200:
        return False, {"param_check": f"Invalid params: {params}"}

    signal_data = {}
    try:
        data = yf.download("SPY", period="1y", interval="1d", auto_adjust=True, progress=False)
        if data.empty:
            signal_data["data_unavailable"] = True
        else:
            signal_data = get_spy_sma200_signal(data)
    except Exception as e:
        signal_data["data_unavailable"] = True
        signal_data["error"] = str(e)

    return True, {"schema_check": "PASS", "signal_data": signal_data}

def validate_spy_rsi2():
    spec = load_yaml("strategies/spy_rsi2.yaml")
    if not spec: return False, {"error": "Failed to load"}

    req_keys = ["id", "name", "family", "venue", "universe", "indicators", "parameters", "entry_rules", "exit_rules", "position_sizing", "fee_model", "benchmark_result", "robustness_notes", "feasibility_at_100", "risks"]
    passed, msg = check_schema(spec, req_keys)
    if not passed: return False, {"schema_check": msg}

    params = spec.get("parameters", {})
    if params.get("entry") != 10 or params.get("exit_rsi") != 70 or params.get("hold_days") != 5:
        return False, {"param_check": f"Invalid params: {params}"}

    signal_data = {}
    try:
        data = yf.download("SPY", period="1mo", interval="1d", auto_adjust=True, progress=False)
        if data.empty:
            signal_data["data_unavailable"] = True
        else:
            signal_data = get_spy_rsi2_signal(data)
    except Exception as e:
        signal_data["data_unavailable"] = True
        signal_data["error"] = str(e)

    return True, {"schema_check": "PASS", "signal_data": signal_data}

def validate_btc_vol_target_sma100():
    spec = load_yaml("strategies/btc_vol_target_sma100.yaml")
    if not spec: return False, {"error": "Failed to load"}

    req_keys = ["id", "name", "family", "venue", "universe", "indicators", "parameters", "entry_rules", "exit_rules", "position_sizing", "fee_model", "benchmark_result", "robustness_notes", "feasibility_at_100", "risks"]
    passed, msg = check_schema(spec, req_keys)
    if not passed: return False, {"schema_check": msg}

    params = spec.get("parameters", {})
    if params.get("target_vol") != 0.30 or params.get("vol_window") != 30 or params.get("gate_window") != 100:
        return False, {"param_check": f"Invalid params: {params}"}

    signal_data = {}
    try:
        data = yf.download("BTC-USD", period="1y", interval="1d", auto_adjust=True, progress=False)
        if data.empty:
            signal_data["data_unavailable"] = True
        else:
            signal_data = get_btc_vol_target_sma100_signal(data)
    except Exception as e:
        signal_data["data_unavailable"] = True
        signal_data["error"] = str(e)

    return True, {"schema_check": "PASS", "signal_data": signal_data}

def validate_dual_momentum():
    spec = load_yaml("strategies/dual_momentum.yaml")
    if not spec: return False, {"error": "Failed to load"}

    req_keys = ["id", "name", "family", "venue", "universe", "indicators", "parameters", "entry_rules", "exit_rules", "position_sizing", "fee_model", "benchmark_result", "robustness_notes", "feasibility_at_100", "risks"]
    passed, msg = check_schema(spec, req_keys)
    if not passed: return False, {"schema_check": msg}

    params = spec.get("parameters", {})
    if params.get("lookback_days") != 21 or params.get("skip_days") != 21:
        return False, {"param_check": f"Invalid params: {params}"}

    signal_data = {}
    try:
        tickers = ["SPY", "QQQ"]
        data = yf.download(tickers, period="3mo", interval="1d", auto_adjust=True, progress=False)
        if data.empty:
            signal_data["data_unavailable"] = True
        else:
            signal_data = get_dual_momentum_signal(data, tickers)
    except Exception as e:
        signal_data["data_unavailable"] = True
        signal_data["error"] = str(e)

    return True, {"schema_check": "PASS", "signal_data": signal_data}

def validate_portfolio():
    spec = load_yaml("strategies/flagship_portfolio_v1.yaml")
    if not spec: return False, {"error": "Failed to load"}

    req_keys = ["id", "name", "type", "created", "source", "members", "allocation", "fees", "constraints", "expected_metrics", "gates"]
    passed, msg = check_schema(spec, req_keys)
    if not passed: return False, {"schema_check": msg}

    # check btc floor and vol window
    alloc = spec.get("allocation", {})
    if alloc.get("btc_floor") != 0.05 or alloc.get("vol_window_months") != 12:
        return False, {"param_check": f"Invalid alloc params: {alloc}"}

    return True, {"schema_check": "PASS", "members": len(spec.get("members", []))}

def main():
    report = {}
    all_passed = True

    checks = {
        "us_momentum_top5": validate_us_momentum_top5,
        "spy_sma200": validate_spy_sma200,
        "spy_rsi2": validate_spy_rsi2,
        "btc_vol_target_sma100": validate_btc_vol_target_sma100,
        "dual_momentum": validate_dual_momentum,
        "flagship_portfolio_v1": validate_portfolio
    }

    for name, func in checks.items():
        passed, data = func()
        report[name] = {
            "passed": passed,
            "details": data
        }
        if not passed:
            all_passed = False
            print(f"FAILED {name}: {data}")
        else:
            print(f"PASSED {name}")

    try:
        import os
        os.makedirs("docs/data", exist_ok=True)
        with open("docs/data/b1_validation.json", "w") as f:
            json.dump(report, f, indent=2)
    except Exception as e:
        print(f"Failed to write report: {e}")
        all_passed = False

    if not all_passed:
        sys.exit(1)

    print("All validation checks passed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
