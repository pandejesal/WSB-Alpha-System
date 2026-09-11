#!/usr/bin/env python3
"""HUNT-SMOOTH-A runner: L1/L2 hunt for slow SMA + vol-scaled long/flat.

Sequential, no subagents. Uses evolve_real backtest (T+1, tiered cost, T=1910 bars)
and gatespec38_tracks thresholds.

Prereg freeze already done via hunt_runner run. This script:
- sweeps spy_sma windows [120,150,170,200,220,250,270,300] + vol-scaled variants
- runs L1 screen (sharpe>=0.50 DD<=35% excess>0)
- runs L2 (perm<=0.05 boot<=0.05 DSR>=0.75 at per-family N, plus full Track2/Track4)
- writes YAML candidates + eval JSONs into hunts/smooth_trend/.../candidates & results
- prints L1/L2 numbers for deliverable

Run: PYTHONPATH=. python scripts/hunt_smooth_A_runner.py
"""
import os, sys, pathlib, json, yaml
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from src.backtest.gatespec38_tracks import TRACKS, check_track_detailed, recompute_dsr

# Use evolve_real as backtest engine
import evolve_real as ev

HUNT_DIR = ROOT / "hunts/smooth_trend/20260909-0607_smooth-trend"
CAND_DIR = HUNT_DIR / "candidates"
RES_DIR = HUNT_DIR / "results"
DOCS_DATA = HUNT_DIR / "docs/data"
PREREG_REF = DOCS_DATA / "cyclesmooth_trend-20260909-0607_smooth-trend_prereg_smooth_trend.md"

# Load data exactly as evolve_real does (CSV panel)
# evolve_real.load_csv loads individual ticker CSVs; we need SPY close series
def load_spy_close():
    df = ev.load_csv("SPY")
    # df index is date, columns include Open,High,Low,Close,Volume (maybe adjusted)
    # evolve_real expects close series: data["SPY"] is likely Close
    # Inspect evolve_real startup
    return df

# Replicate evolve_real data loading: it loads multiple tickers but for spy_sma we just need SPY
# Let's inspect how evolve_real initializes data for run_family
# It has global data dict loaded at startup via _load_all? Let's directly call its loading block.

# Patch: build data dict manually
def build_data():
    # Load SPY CSV
    spy_df = ev.load_csv("SPY")
    # spy_df columns? print debug
    # evolve_real stores data["SPY"] as Series close? Check run_family: sig_spy_sma(data["SPY"], p["window"])
    # So data["SPY"] is likely a Series of closes (index date)
    # Let's see what load_csv returns vs what evolve_real stores
    # Look at evolve_real main: data = { ... } - search
    import pathlib
    # Try to replicate evolve_real's data building
    # From evolve_real lines ~700: data dict building
    # We'll read that section
    return spy_df

# Instead directly inspect evolve_real's data loading code path
# Let's just load via ev and check what it does by reading its source for init
import inspect, textwrap
src = inspect.getsource(ev)
# Find data initialization
for i, line in enumerate(src.split("\n")[650:800], start=651):
    print(f"{i}: {line}")
    if i>750:
        break
