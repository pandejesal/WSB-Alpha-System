import json
import os
import sys
from unittest.mock import patch
from collections import defaultdict
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.build_paper_months import month_key, monthly_pnl, get_spy_returns

def test_month_key():
    assert month_key("2026-07-01T10:00:00Z") == "2026-07"
    assert month_key("2026-08") == "2026-08"
    assert month_key(None) is None
    assert month_key(123) is None

def test_monthly_pnl():
    fills_doc = {
        "fills": [
            {"ts": "2026-07-01T10:00:00Z", "side": "buy", "qty": "2.0", "avg_px": "100.0", "status": "FILLED"},
            {"ts": "2026-07-15T10:00:00Z", "side": "sell", "qty": "2.0", "avg_px": "110.0", "status": "FILLED"},
            {"ts": "2026-08-01T10:00:00Z", "side": "buy", "qty": "1.0", "avg_px": "50.0", "status": "FILLED"},
            {"ts": "2026-08-15T10:00:00Z", "side": "sell", "qty": "1.0", "avg_px": "45.0", "status": "FILLED"},
            {"ts": "2026-09-01T10:00:00Z", "side": "buy", "qty": "1.0", "avg_px": "50.0", "status": "SUBMITTED"}
        ]
    }

    pnl = monthly_pnl(fills_doc)
    assert pnl == {"2026-07": 20.0, "2026-08": -5.0}

@patch('yfinance.download')
def test_get_spy_returns(mock_download):
    # Mock SPY data
    dates = pd.date_range(start="2026-07-01", end="2026-08-31", freq="B")
    mock_df = pd.DataFrame(index=dates)
    mock_df['Open'] = [100.0] * len(dates)
    mock_df['Close'] = [100.0] * len(dates)

    # Make July close higher
    july_last = mock_df[mock_df.index.strftime('%Y-%m') == '2026-07'].index[-1]
    mock_df.at[july_last, 'Close'] = 110.0

    # Make August close lower
    august_last = mock_df[mock_df.index.strftime('%Y-%m') == '2026-08'].index[-1]
    mock_df.at[august_last, 'Close'] = 90.0

    mock_download.return_value = mock_df

    returns = get_spy_returns(["2026-07", "2026-08"])

    assert returns["2026-07"] == pytest.approx(0.1) # (110 / 100) - 1
    assert returns["2026-08"] == pytest.approx(-0.1) # (90 / 100) - 1

def test_script_idempotency_and_precharter(tmp_path):
    import scripts.build_paper_months as bpm
    bpm.OPS_DIR = str(tmp_path)
    bpm.FILLS_PATH = os.path.join(bpm.OPS_DIR, "fills.json")
    bpm.OUT_PATH = os.path.join(bpm.OPS_DIR, "paper_months.jsonl")
    bpm.BASE_EQUITY = 100_000.0
    bpm.CHARTER_MONTH = "2026-08"

    fills_doc = {
        "fills": [
            {"ts": "2026-07-01T10:00:00Z", "side": "buy", "qty": "100.0", "avg_px": "100.0", "status": "FILLED"},
            {"ts": "2026-07-15T10:00:00Z", "side": "sell", "qty": "100.0", "avg_px": "101.0", "status": "FILLED"},
            {"ts": "2026-08-01T10:00:00Z", "side": "buy", "qty": "100.0", "avg_px": "100.0", "status": "FILLED"},
            {"ts": "2026-08-15T10:00:00Z", "side": "sell", "qty": "100.0", "avg_px": "90.0", "status": "FILLED"}
        ]
    }
    os.makedirs(bpm.OPS_DIR, exist_ok=True)
    with open(bpm.FILLS_PATH, "w") as f:
        json.dump(fills_doc, f)

    with patch('yfinance.download') as mock_download:
        dates = pd.date_range(start="2026-07-01", end="2026-08-31", freq="B")
        mock_df = pd.DataFrame(index=dates)
        mock_df['Open'] = [100.0] * len(dates)
        mock_df['Close'] = [100.0] * len(dates)
        # SPY +2% in July, -5% in August
        mock_df.at[mock_df[mock_df.index.strftime('%Y-%m') == '2026-07'].index[-1], 'Close'] = 102.0
        mock_df.at[mock_df[mock_df.index.strftime('%Y-%m') == '2026-08'].index[-1], 'Close'] = 95.0
        mock_download.return_value = mock_df

        # Run 1
        bpm.main()

        assert os.path.exists(bpm.OUT_PATH)
        lines = [json.loads(line) for line in open(bpm.OUT_PATH)]
        assert len(lines) == 2

        # Check July (pre-charter)
        july = next(l for l in lines if l["month"] == "2026-07")
        assert july["strategy_return_net"] == 0.001
        assert july["spy_return_net_same_window"] == 0.02
        assert july["absolute_green"] is True
        assert july["excess_green"] is None
        assert "pre-charter" in july["note"]

        # Check August (post-charter)
        aug = next(l for l in lines if l["month"] == "2026-08")
        assert aug["strategy_return_net"] == -0.01
        assert aug["spy_return_net_same_window"] == -0.05
        assert aug["absolute_green"] is False
        assert aug["excess_green"] is True
        assert "note" not in aug

        # Run 2: ensure idempotency (should just rewrite same data)
        bpm.main()
        lines2 = [json.loads(line) for line in open(bpm.OUT_PATH)]
        assert lines == lines2

        # Make strategy negative in July to test absolute_green logic updates
        fills_doc["fills"][1]["avg_px"] = "99.0"
        with open(bpm.FILLS_PATH, "w") as f:
            json.dump(fills_doc, f)

        bpm.main()
        lines3 = [json.loads(line) for line in open(bpm.OUT_PATH)]
        july_new = next(l for l in lines3 if l["month"] == "2026-07")
        assert july_new["strategy_return_net"] == -0.001
        assert july_new["absolute_green"] is False
        assert july_new["excess_green"] is None # Still pre-charter
