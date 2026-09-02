import json
import os
import sys
from collections import defaultdict
from tempfile import mkstemp

import yfinance as yf
import pandas as pd

# Constants
OPS_DIR = "docs/data/ops"
FILLS_PATH = f"{OPS_DIR}/fills.json"
OUT_PATH = f"{OPS_DIR}/paper_months.jsonl"
BASE_EQUITY = 100_000.0  # As per baseline_paper_track.py
CHARTER_MONTH = "2026-08"

def load_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def month_key(ts):
    try:
        return ts[:7]
    except (TypeError, IndexError):
        return None

def monthly_pnl(fills_doc):
    if not isinstance(fills_doc, dict):
        return {}
    monthly = defaultdict(float)
    has_any = False
    for fill in fills_doc.get("fills", []):
        if fill.get("status") != "FILLED":
            continue
        mk = month_key(fill.get("ts", ""))
        if not mk:
            continue
        qty = float(fill.get("qty") or 0.0)
        px = float(fill.get("avg_px") or 0.0)
        if fill.get("side") == "sell":
            monthly[mk] += qty * px
            has_any = True
        elif fill.get("side") == "buy":
            monthly[mk] -= qty * px
    if not has_any:
        return {}
    return {k: round(v, 2) for k, v in sorted(monthly.items())}

def get_spy_returns(months):
    """
    Downloads SPY data for the needed months and calculates the monthly return.
    Return dictionary: { 'YYYY-MM': return_float }
    """
    spy_returns = {}
    if not months:
        return spy_returns

    # Determine start and end date to fetch all at once
    sorted_months = sorted(months)
    start_str = f"{sorted_months[0]}-01"

    # Calculate end of the last month roughly
    last_month = sorted_months[-1]
    y, m = int(last_month[:4]), int(last_month[5:7])
    if m == 12:
        end_y, end_m = y + 1, 1
    else:
        end_y, end_m = y, m + 1
    end_str = f"{end_y:04d}-{end_m:02d}-01"

    # Fetch data
    try:
        # We'll use the default yf.download but catch errors
        df = yf.download("SPY", start=start_str, end=end_str, progress=False, auto_adjust=True)
    except Exception as e:
        print(f"Error fetching SPY data: {e}")
        return {}

    if df is None or df.empty:
        return {}

    # Standardize column index structure if it's MultiIndex (yfinance 0.2.x behavior)
    if isinstance(df.columns, pd.MultiIndex):
        try:
             close_col = df.xs("SPY", level=1, axis=1)['Close']
             open_col = df.xs("SPY", level=1, axis=1)['Open']
        except KeyError:
             close_col = df['Close']
             open_col = df['Open']
    else:
        close_col = df['Close']
        open_col = df['Open']

    # Compute per-month returns
    for month in months:
        month_df = df[df.index.strftime('%Y-%m') == month]
        if month_df.empty:
            spy_returns[month] = 0.0
            continue

        first_open = float(open_col.loc[month_df.index[0]])
        last_close = float(close_col.loc[month_df.index[-1]])

        if first_open > 0:
            spy_returns[month] = (last_close / first_open) - 1.0
        else:
            spy_returns[month] = 0.0

    return spy_returns

def main():
    fills_doc = load_json(FILLS_PATH)
    pnl_by_month = monthly_pnl(fills_doc)

    if not pnl_by_month:
        print("No valid fills found for monthly bucketing.")
        sys.exit(0)

    spy_returns = get_spy_returns(list(pnl_by_month.keys()))

    # Read existing lines if any
    existing_lines = []
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        existing_lines.append(json.loads(line))
                    except Exception:
                        pass

    existing_dict = {rec.get("month"): rec for rec in existing_lines if rec.get("month")}

    # Process each month
    for month, pnl in pnl_by_month.items():
        strategy_return_net = round(pnl / BASE_EQUITY, 6)
        spy_ret = round(spy_returns.get(month, 0.0), 6)
        absolute_green = strategy_return_net > 0

        rec = {
            "month": month,
            "strategy_return_net": strategy_return_net,
            "spy_return_net_same_window": spy_ret,
            "absolute_green": absolute_green,
        }

        is_pre_charter = month < CHARTER_MONTH

        if is_pre_charter:
            rec["excess_green"] = None
            rec["note"] = "pre-charter, excess not tracked"
        else:
            rec["excess_green"] = strategy_return_net > spy_ret

        existing_dict[month] = rec

    # Write idempotently with atomicity
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    fd, temp_path = mkstemp(dir=os.path.dirname(OUT_PATH))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for month in sorted(existing_dict.keys()):
                f.write(json.dumps(existing_dict[month]) + "\n")

        # Atomic replace
        os.replace(temp_path, OUT_PATH)
    except Exception as e:
        os.remove(temp_path)
        raise e

    print(f"[build_paper_months] Updated {OUT_PATH} with {len(pnl_by_month)} months tracked.")

if __name__ == "__main__":
    main()
