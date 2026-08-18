import argparse
import datetime
import json
import os
import sys

import pandas as pd
import yaml
import yfinance as yf

from src.ops.signals import (
    get_btc_vol_target_sma100_signal,
    get_dual_momentum_signal,
    get_spy_rsi2_signal,
    get_spy_sma200_signal,
    get_us_momentum_top5_signal,
)

# Constants
# Top ~100 US large-cap liquid equities (from S&P 100), no penny/ADR/REITs
MOMENTUM_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "BRK-B", "LLY", "AVGO",
    "JPM", "TSLA", "WMT", "UNH", "XOM", "V", "PG", "MA", "JNJ", "HD",
    "COST", "MRK", "ABBV", "CVX", "CRM", "BAC", "KO", "NFLX", "AMD", "PEP",
    "TMO", "LIN", "WFC", "DIS", "ADBE", "MCD", "CSCO", "ABT", "INTU", "QCOM",
    "IBM", "GE", "CAT", "AMAT", "TXN", "DHR", "AXP", "PFE", "PM", "NOW",
    "ISRG", "SYK", "SPGI", "HON", "BA", "COP", "RTX", "LMT", "NEE", "UPS",
    "BLK", "GS", "MS", "MDT", "C", "SBUX", "BMY", "DE", "BKNG", "GILD",
    "CVS", "INTC", "ADP", "CI", "MDLZ", "TJX", "CB", "MMC", "VRTX", "REGN",
    "ADI", "ZTS", "BSX", "PGR", "FI", "KLAC", "SNPS", "CDNS", "ETN", "PANW",
    "MU", "LRCX", "GPN", "TGT", "SLB", "MO", "USB", "PNC", "T", "VZ"
]

def load_yaml(filepath):
    if not os.path.exists(filepath):
        print(f"Error: Required file {filepath} not found.")
        sys.exit(1)
    try:
        with open(filepath, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        sys.exit(1)

def check_freshness(data: pd.DataFrame, max_days: int = 3) -> bool:
    if data is None or data.empty:
        return False
    # Ensure timezone awareness is handled or stripped
    last_date = data.index[-1]
    if last_date.tzinfo is not None:
         last_date = last_date.tz_localize(None)
    now = pd.Timestamp.now().normalize()
    return (now - last_date).days <= max_days

def run_check_mode():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    date_str = now_utc.strftime("%Y-%m-%d")
    short_sha = os.environ.get("GITHUB_SHA", "local")[:7]
    run_id = f"{now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')}-{short_sha}"

    plan_data = {
        "run_id": run_id,
        "date": date_str,
        "mode": "check",
        "sleeves": [],
        "portfolio": {
            "weights": {},
            "rebalance_due": False,
            "btc_floor_applied": False,
            "below_min_notional": []
        },
        "blocked": [],
        "data_unavailable": [],
        "warnings": []
    }

    heartbeat_data = {
        "run_id": run_id,
        "ts": now_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),
        "mode": "check",
        "result": "ok",
        "orders_submitted": 0,
        "alerts": []
    }

    # Load Strategies
    strategy_yamls = [
        "strategies/flagship_portfolio_v1.yaml",
        "strategies/us_momentum_top5.yaml",
        "strategies/spy_sma200.yaml",
        "strategies/spy_rsi2.yaml",
        "strategies/btc_vol_target_sma100.yaml",
        "strategies/dual_momentum.yaml"
    ]
    for p in strategy_yamls:
        load_yaml(p)

    # Freshness Gate
    tickers_to_fetch = ["SPY", "QQQ", "AGG", "BTC-USD"] + MOMENTUM_UNIVERSE
    try:
        data = yf.download(tickers_to_fetch, period="1y", interval="1d", auto_adjust=True, progress=False)
    except Exception:
        data = None

    if data is None or data.empty:
        plan_data["blocked"].append("STALE_DATA")
        plan_data["warnings"].append("Failed to fetch data for all assets.")
        heartbeat_data["alerts"].append("WARN: Failed to fetch market data.")
        write_outputs(plan_data, heartbeat_data)
        sys.exit(0)

    # Check if latest SPY close is fresh
    if "SPY" in data['Close'] and not data['Close']['SPY'].dropna().empty:
         spy_data = data['Close']['SPY'].dropna()
         last_date = spy_data.index[-1]
         if last_date.tzinfo is not None:
             last_date = last_date.tz_localize(None)
         now = pd.Timestamp.now().normalize()
         if (now - last_date).days > 3:
             plan_data["blocked"].append("STALE_DATA")
             plan_data["warnings"].append(f"SPY data is stale. Last date: {last_date}")
             heartbeat_data["alerts"].append("WARN: Market data is stale (SPY).")
             write_outputs(plan_data, heartbeat_data)
             sys.exit(0)
    else:
        # If SPY missing entirely
        plan_data["blocked"].append("STALE_DATA")
        plan_data["warnings"].append("SPY data missing entirely.")
        heartbeat_data["alerts"].append("WARN: Market data missing (SPY).")
        write_outputs(plan_data, heartbeat_data)
        sys.exit(0)

    # Process sleeves
    # 1. us_momentum_top5
    mom_data = get_us_momentum_top5_signal(data, MOMENTUM_UNIVERSE)
    targets = []
    if mom_data.get("data_unavailable"):
        plan_data["data_unavailable"].append("us_momentum_top5")
        plan_data["sleeves"].append({
            "id": "us_momentum_top5",
            "signal": {"top5": [], "momentum_scores": {}},
            "targets": []
        })
    else:
        if "top_5" in mom_data:
            for t in mom_data["top_5"]:
                 targets.append({"symbol": t, "notional_pct": 0.2, "side": "buy", "drift_ok": True})

        plan_data["sleeves"].append({
            "id": "us_momentum_top5",
            "signal": {"top5": mom_data.get("top_5", []), "momentum_scores": mom_data.get("momenta", {})},
            "targets": targets
        })

    # 2. spy_sma200
    if "SPY" in data['Close'] and not data['Close']['SPY'].dropna().empty:
        spy_df = data['Close']['SPY'].dropna()
        sma200_data = get_spy_sma200_signal(spy_df)
    else:
        sma200_data = {"data_unavailable": True}

    if sma200_data.get("data_unavailable"):
        plan_data["data_unavailable"].append("spy_sma200")
        plan_data["sleeves"].append({
             "id": "spy_sma200", "signal": {"state": "OUT", "close": 0.0, "sma200": 0.0}, "targets": []
        })
    else:
        plan_data["sleeves"].append({
            "id": "spy_sma200",
            "signal": {"state": "IN" if sma200_data.get("signal") == "BUY" else "OUT",
                       "close": sma200_data.get("last_close"),
                       "sma200": sma200_data.get("sma200")},
            "targets": []
        })

    # 3. spy_rsi2
    if "SPY" in data['Close'] and not data['Close']['SPY'].dropna().empty:
        rsi2_data = get_spy_rsi2_signal(spy_df) # reuse spy_df
    else:
        rsi2_data = {"data_unavailable": True}

    if rsi2_data.get("data_unavailable"):
        plan_data["data_unavailable"].append("spy_rsi2")
        plan_data["sleeves"].append({
             "id": "spy_rsi2", "signal": {"rsi2": 0.0, "sma5": 0.0, "action": "HOLD"}, "targets": []
        })
    else:
        rsi2_val = rsi2_data.get("rsi2")
        sma5_val = rsi2_data.get("sma5")
        close_val = rsi2_data.get("last_close")
        action = "HOLD"
        if rsi2_val is not None and rsi2_val < 10:
            action = "BUY"
        elif sma5_val is not None and close_val is not None and (close_val > sma5_val or (rsi2_val is not None and rsi2_val > 70)):
            action = "EXIT"

        plan_data["sleeves"].append({
            "id": "spy_rsi2",
            "signal": {"rsi2": rsi2_val, "sma5": sma5_val, "action": action},
            "targets": []
        })

    # 4. btc_vol_target_sma100
    if "BTC-USD" in data['Close'] and not data['Close']['BTC-USD'].dropna().empty:
         btc_df = data['Close']['BTC-USD'].dropna()
         if not check_freshness(btc_df, max_days=3):
             btc_data = {"data_unavailable": True}
         else:
             btc_data = get_btc_vol_target_sma100_signal(btc_df)
    else:
         btc_data = {"data_unavailable": True}

    if btc_data.get("data_unavailable"):
        plan_data["data_unavailable"].append("btc_vol_target_sma100")
        plan_data["sleeves"].append({
             "id": "btc_vol_target_sma100", "signal": {"exposure": 0.0, "realized_vol": 0.0, "regime": "OFF"}, "targets": []
        })
    else:
        exp = btc_data.get("target_exposure", 0.0)
        regime = "ON" if exp > 0 else "OFF"
        plan_data["sleeves"].append({
            "id": "btc_vol_target_sma100",
            "signal": {"exposure": exp, "realized_vol": btc_data.get("realized_vol", 0.0), "regime": regime},
            "targets": []
        })

    # 5. dual_momentum
    dm_data = get_dual_momentum_signal(data)
    if dm_data.get("data_unavailable"):
        plan_data["data_unavailable"].append("dual_momentum")
        plan_data["sleeves"].append({
             "id": "dual_momentum", "signal": {"leg": "AGG", "mom_spy": 0.0, "mom_qqq": 0.0}, "targets": []
        })
    else:
        moms = dm_data.get("momenta", {})
        plan_data["sleeves"].append({
            "id": "dual_momentum",
            "signal": {"leg": dm_data.get("signal", "AGG"), "mom_spy": moms.get("SPY", 0.0), "mom_qqq": moms.get("QQQ", 0.0)},
            "targets": []
        })

    # Portfolio weights calculation
    returns_file = "docs/data/portfolio/monthly_returns.csv"
    weights = {
        "us_momentum_top5": 0.0,
        "spy_sma200": 0.0,
        "spy_rsi2": 0.0,
        "btc_vol_target_sma100": 0.0,
        "dual_momentum": 0.0
    }

    if os.path.exists(returns_file):
        try:
            ret_df = pd.read_csv(returns_file, index_col=0)
            if len(ret_df) >= 12:
                recent_12 = ret_df.iloc[-12:]
                stds = recent_12.std()

                inv_vol = {}
                for col in weights:
                    if col in stds and stds[col] > 0 and col not in plan_data["data_unavailable"]:
                        inv_vol[col] = 1.0 / stds[col]
                    else:
                        inv_vol[col] = 0.0

                total_inv_vol = sum(inv_vol.values())
                if total_inv_vol > 0:
                    for k in weights:
                        weights[k] = round(inv_vol[k] / total_inv_vol, 6)
        except Exception as e:
            plan_data["warnings"].append(f"Weight calculation failed: {e}")

    # BTC floor
    if "btc_vol_target_sma100" not in plan_data["data_unavailable"]:
         btc_w = weights["btc_vol_target_sma100"]
         if btc_w < 0.05 and btc_w > 0: # Only floor if it was going to have *some* weight originally, wait spec says "if btc weight < 0.05 force 0.05"
             weights["btc_vol_target_sma100"] = 0.05
             plan_data["portfolio"]["btc_floor_applied"] = True

             # renormalize others
             other_sum = sum(v for k, v in weights.items() if k != "btc_vol_target_sma100")
             if other_sum > 0:
                 scale = (1.0 - 0.05) / other_sum
                 for k in weights:
                     if k != "btc_vol_target_sma100":
                         weights[k] = round(weights[k] * scale, 6)
         elif btc_w == 0.0 and sum(weights.values()) > 0:
             # Even if calculated 0 due to some issue (but not missing data)?
             # Let's enforce strictly if not missing data.
             weights["btc_vol_target_sma100"] = 0.05
             plan_data["portfolio"]["btc_floor_applied"] = True
             other_sum = sum(v for k, v in weights.items() if k != "btc_vol_target_sma100")
             if other_sum > 0:
                 scale = (1.0 - 0.05) / other_sum
                 for k in weights:
                     if k != "btc_vol_target_sma100":
                         weights[k] = round(weights[k] * scale, 6)

    # Min notional flags (assuming $100 total equity)
    equity = 100.0
    for k, w in weights.items():
        if w > 0:
            if k == "btc_vol_target_sma100":
                if w * equity < 5.0:
                    plan_data["portfolio"]["below_min_notional"].append(k)
            else:
                if w * equity < 1.0:
                    plan_data["portfolio"]["below_min_notional"].append(k)

    plan_data["portfolio"]["weights"] = weights

    write_outputs(plan_data, heartbeat_data)
    print(f"Daily Check Run Complete: {run_id}")

def write_outputs(plan_data, heartbeat_data):
    os.makedirs("docs/data/ops", exist_ok=True)
    with open("docs/data/ops/plan.json", "w") as f:
        json.dump(plan_data, f, indent=2)
    with open("docs/data/ops/heartbeat.json", "w") as f:
        json.dump(heartbeat_data, f, indent=2)

def main():
    parser = argparse.ArgumentParser(description="WSB-Alpha-System Ops Engine")
    parser.add_argument("--mode", choices=["check"], required=True, help="Mode to run the ops engine in")

    args = parser.parse_args()

    if args.mode == "check":
        run_check_mode()
    else:
        print(f"Error: Mode {args.mode} is not supported in Phase A.")
        sys.exit(1)

if __name__ == "__main__":
    main()
