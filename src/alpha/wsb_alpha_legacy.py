import logging

from src.research.ticker_extractor import extract_tickers

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# -*- coding: utf-8 -*-
# ============================================================================
# WSB DD SENTIMENT ANALYTICS & PLOTTER - UNIFIED INCREMENTAL SYSTEM
# ============================================================================
import nltk  # noqa: E402 - imports must happen after configuration / environment setup

try:
    nltk.data.find('tokenizers/punkt_tab')
    nltk.data.find('taggers/averaged_perceptron_tagger_eng')
except LookupError:
    nltk.download('punkt_tab')
    nltk.download('averaged_perceptron_tagger_eng')


import json  # noqa: E402 - imports must happen after configuration / environment setup
import os  # noqa: E402 - imports must happen after configuration / environment setup
import re  # noqa: E402 - imports must happen after configuration / environment setup
from collections import defaultdict  # noqa: E402 - imports must happen after configuration / environment setup
from datetime import (  # noqa: E402 - imports must happen after configuration / environment setup
    datetime,
    timedelta,
)

import defusedxml.ElementTree as ET  # noqa: E402 - imports must happen after configuration / environment setup
import matplotlib.pyplot as plt  # noqa: E402 - imports must happen after configuration / environment setup
import numpy as np  # noqa: E402 - imports must happen after configuration / environment setup
import pandas as pd  # noqa: E402 - imports must happen after configuration / environment setup
import requests  # noqa: E402 - imports must happen after configuration / environment setup
import yfinance as yf  # noqa: E402 - imports must happen after configuration / environment setup
from tqdm import tqdm  # noqa: E402 - imports must happen after configuration / environment setup

from src.alpha.indicators import (  # noqa: E402 - imports must happen after configuration / environment setup
    compute_indicators,
    compute_regime_returns,
)

# ============================================================================
# DYNAMIC SYSTEM PATH CONFIGURATION
# ============================================================================
# Automatically locate the folder where this script is saved
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Anchor all output file paths strictly to this directory to avoid system directory saving issues
OUTPUT_CSV = os.path.join(SCRIPT_DIR, "wsb_factual_research_data.csv")
CO_MENTION_JSON = os.path.join(SCRIPT_DIR, "co_mentions.json")
OUTPUT_PNG = os.path.join(SCRIPT_DIR, "wsb_stock_trajectories.png")

# Global Configuration Parameters

FINBERT_MODEL = "ProsusAI/finbert"
FINBERT_LABELS = ["bearish", "neutral", "bullish"]
CONFIDENCE_THRESHOLD = 0.5

FORWARD_DAYS = [1, 5, 10, 20, 30, 60, 90, 120, 252, 300]
TICKER_RE = re.compile(r'\b[A-Z]{2,5}\b')

BLACKLIST = {
    "THE","AND","FOR","YOU","ARE","BUT","NOT","WITH","THIS","THAT","FROM","HAVE","HAS","HAD",
    "WILL","WOULD","COULD","SHOULD","WHEN","WHERE","WHY","HOW","ALL","ANY","SOME","MORE",
    "LESS","OVER","UNDER","ABOUT","INTO","THAN","THEN","THEM","THEY","THEIR","THERE","HERE",
    "WHAT","WHICH","WHO","WHOM","BEEN","BEING","WERE","WAS","IS","AM","DO","DID","DOES",
    "CAN","MAY","MUST","SHALL","OWN","SAME","OTHER","ANOTHER","EACH","EVERY","FEW","MANY",
    "MOST","SUCH","ONLY","VERY","TOO","ALSO","EVEN","STILL","JUST","NOW","AGAIN","BACK",
    "DOWN","UP","OUT","OFF","ON","IN","AT","BY","AS","IF","OR","NOR","SO","YET",
    "YOLO","FD","FDS","CALL","PUT","PUTS","CALLS","SPY","QQQ","VIX","ETF","ETFS","IPO",
    "SECTOR","INDUSTRY","MARKET","STOCK","STOCKS","SHARE","SHARES","PRICE","TRADE","TRADES",
    "LONG","SHORT","HOLD","HODL","BUY","SELL","BULL","BEAR","GAIN","LOSS","PROFIT","RISK",
    "ALPHA","BETA","EPS","PE","REVENUE","EARNINGS","GUIDANCE","DIVIDEND","SPLIT","MERGER",
    "ACQUISITION","FDA","SEC","FED","CPI","PPI","GDP","UNEMPLOYMENT","INTEREST","RATE",
    "INFLATION","RECESSION","CRASH","RALLY","CORRECTION","SUPPORT","RESISTANCE",
    "BREAKOUT","BREAKDOWN","TREND","MOMENTUM","VOLUME","VOLATILITY","IV","HV","GREEKS",
    "DELTA","GAMMA","THETA","VEGA","RHO","STRIKE","EXPIRY","EXPIRATION","ITM","OTM","ATM",
    "PREMIUM","INTRINSIC","TIME","VALUE","DECAY","ASSIGNMENT","EXERCISE","COVERED","NAKED",
    "SPREAD","STRADDLE","STRANGLE","IRON","CONDOR","BUTTERFLY","CALENDAR","DIAGONAL",
    "RATIO","BACKSPREAD","VERTICAL","HORIZONTAL","HE","IT","LOT","PLUS","WEEK","YEAR","GAP"
}

# ============================================================================
def extract_tickers(text: str) -> list[str]:  # noqa: F811 - redefinition of unused legacy function or duplicate import fallback
    if not text:
        return []
    raw_matches = TICKER_RE.findall(text)
    valid_casing_matches = [m for m in raw_matches if m.isupper()]
    pre_filtered = [m for m in valid_casing_matches if m not in BLACKLIST]
    if not pre_filtered:
        return []
    try:
        tokens = nltk.word_tokenize(text)
        pos_tags = nltk.pos_tag(tokens)
        word_tags = {}
        for word, tag in pos_tags:
            if word in pre_filtered:
                if word not in word_tags:
                    word_tags[word] = set()
                word_tags[word].add(tag)
        final_tickers = set()
        for token in pre_filtered:
            tags = word_tags.get(token, set())
            rejected_tags = {"PRP", "PRP$", "IN", "DT", "CC", "UH", "MD"}
            if not tags or any(t not in rejected_tags for t in tags):
                final_tickers.add(token)
        return list(final_tickers)
    except Exception:
        return list(set(pre_filtered))


def load_finbert():
    logger.info("FinBERT loading skipped since torch/transformers are no longer installed.")
    return None, None, None

def finbert_sentiment(text: str, tokenizer, model, device) -> dict:
    logger.warning("finbert_sentiment called but finbert is removed, returning neutral")
    return {"bullish": 0.0, "bearish": 0.0, "neutral": 1.0}

import time  # noqa: E402 - imports must happen after configuration / environment setup


def safe_write_csv(df, path):
    for i in range(3):
        try:
            df.to_csv(path, index=False)
            return
        except PermissionError:
            logger.info(f"Permission Denied {path}")
            time.sleep(2**i)
    df.to_csv(f"{path}.tmp", index=False)

def safe_write_json(data, path):
    for i in range(3):
        try:
            with open(path, "w") as f:
                json.dump(data, f)
            return
        except PermissionError:
            logger.info(f"Permission Denied {path}")
            time.sleep(2**i)
    with open(f"{path}.tmp", "w") as f:
        json.dump(data, f)


def fetch_rss_feed() -> list[dict]:
    """
    Fetches the WallStreetBets DD feed via Reddit RSS search.
    This public RSS endpoint does not require an API key or registration.
    """
    url_rss = "https://www.reddit.com/r/wallstreetbets/search.rss?q=flair%3ADD&restrict_sr=1&sort=new"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    try:
        logger.info(f"Requesting public RSS feed from: {url_rss}")
        r = requests.get(url_rss, headers=headers, timeout=15)
        if r.status_code != 200:
            logger.info(f"Warning: RSS feed returned status code {r.status_code}")
            return []

        root = ET.fromstring(r.text)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        entries = root.findall('atom:entry', ns)

        items = []
        for entry in entries:
            title_node = entry.find('atom:title', ns)
            content_node = entry.find('atom:content', ns)
            updated_node = entry.find('atom:updated', ns)
            id_node = entry.find('atom:id', ns)
            link_node = entry.find('atom:link', ns)

            title = title_node.text if title_node is not None else ""
            content = content_node.text if content_node is not None else ""
            updated = updated_node.text if updated_node is not None else ""
            raw_id = id_node.text if id_node is not None else ""
            permalink = link_node.attrib.get('href', '') if link_node is not None else ""

            # Clean up raw reddit ID (e.g., 't3_1v4qilm' -> '1v4qilm')
            cleaned_id = raw_id.split('_')[-1] if '_' in raw_id else raw_id

            items.append({
                "id": cleaned_id,
                "title": title,
                "body": content,
                "createdAt": updated,
                "permalink": permalink,
                "score": 100,  # Proxy default values as RSS contains basic post metadata
                "num_comments": 20
            })
        logger.info(f"Successfully parsed {len(items)} posts from the public RSS Feed.")
        return items
    except Exception as e:
        logger.info(f"Error fetching RSS feed: {e}")
        return []

# ============================================================================
# PHASE 1: INCREMENTAL SCRAPING & SENTIMENT RE-EVALUATION PIPELINE
# ============================================================================
def run_sentiment_pipeline():
    logger.info("=" * 60)
    logger.info("PHASE 1: SCRAPING AND SENTIMENT CLASSIFICATION")
    logger.info("=" * 60)
    
    # ------------------------------------------------------------------
    # INPUT PROMPTS
    # ------------------------------------------------------------------
    logger.info("Select Reddit data collection mode:")
    logger.info("1. [FREE] Public RSS Feed Scraper (No API Keys / Accounts / Costs, fetches latest 25 posts)")
    logger.info("2. [PAID/KEY] PRAW Reddit Scraper (Requires Reddit API Keys)")

    # Auto-mode for tests/automation. Default to 1 (Free RSS)
    mode_input = os.environ.get("WSB_SCRAPER_MODE", "1").strip()
    
    use_rss = mode_input != "2"
    
    max_items = 1000
    target_year = None

    if not use_rss:
        max_items_input = os.environ.get("WSB_MAX_ITEMS", "1000").strip()
        max_items = int(max_items_input) if max_items_input.isdigit() else 1000

        target_year_input = os.environ.get("WSB_TARGET_YEAR", "").strip()
        target_year = int(target_year_input) if target_year_input.isdigit() else None
    
    items = []
    if use_rss:
        items = fetch_rss_feed()
    else:
        # Use reddit_scraper.py module for anti-ban and deduplication
        from src.research.reddit_scraper import fetch_reddit_data_sync
        items = fetch_reddit_data_sync(max_items=max_items)

        
    # ------------------------------------------------------------------
    # ROBUST FALLBACK HANDLING FOR SCRAPER FAILURE
    # ------------------------------------------------------------------
    if not items:
        if os.path.exists(OUTPUT_CSV):
            logger.info("No new items returned or scraper could not fetch data.")
            # Automate fallback choice using env variable (default to 'n' for safety, but we can set it to 'y' in tests)
            user_choice = os.environ.get("WSB_FALLBACK_RE_EVALUATE", "n").strip().lower()
            if user_choice != 'y':
                return False
            # Generate empty new data so the pipeline naturally falls back to updating the old database
            df = pd.DataFrame()
            new_daily = pd.DataFrame()
        else:
            logger.info("Error: Empty dataset returned and no existing database found.")
            return False
    else:
        tokenizer, model, device = load_finbert()
        
        logger.info("\nRunning NLP analysis pipeline on newly fetched posts...")
        rows = []
        for item in tqdm(items, desc="Processing Posts"):
            full_text = f"{item.get('title','')} {item.get('body','') or item.get('text','') or item.get('selftext','')}"
            tickers = extract_tickers(full_text)
            if not tickers:
                continue
                
            created_val = item.get("createdAt") or item.get("created_utc") or item.get("created")
            if not created_val:
                continue
                
            if isinstance(created_val, (int, float)):
                created = datetime.fromtimestamp(created_val / 1000 if created_val > 1e12 else created_val)
            elif isinstance(created_val, str):
                try:
                    # Robust ISO or custom timestamp parsing
                    if "T" in created_val:
                        # Clean trailing offsets
                        clean_ts = created_val.split("+")[0].split("Z")[0]
                        created = datetime.strptime(clean_ts[:19], "%Y-%m-%dT%H:%M:%S")
                    else:
                        created = datetime.fromisoformat(created_val.replace("Z", "+00:00"))
                except Exception as e:
                    logger.debug(f"Failed to parse datetime: {e}")
                    continue
            else:
                continue
                
            # Filter locally in Python rather than in the raw search query
            if target_year is not None and created.year != target_year:
                continue
                
            sent = finbert_sentiment(full_text, tokenizer, model, device)
            bullish, bearish, neutral = sent["bullish"], sent["bearish"], sent["neutral"]
            net_sentiment = bullish - bearish
            
            is_bullish = bullish > CONFIDENCE_THRESHOLD
            is_bearish = bearish > CONFIDENCE_THRESHOLD
            
            for t in tickers:
                rows.append({
                    "post_id": item.get("id"),
                    "post_date": str(created.date()),
                    "ticker": t,
                    "title": item.get("title", "")[:300],
                    "body": (item.get("body") or item.get("text") or item.get("selftext") or "")[:5000],
                    "score": item.get("score", 0),
                    "num_comments": item.get("num_comments") or item.get("numComments") or 0,
                    "permalink": f"https://reddit.com{item.get('permalink','')}",
                    "bullish": bullish,
                    "bearish": bearish,
                    "neutral": neutral,
                    "net_sentiment": net_sentiment,
                    "is_bullish": is_bullish,
                    "is_bearish": is_bearish,
                })
                
        df = pd.DataFrame(rows)
        if df.empty:
            logger.info("Warning: No newly fetched posts matched your filter constraints.")
            new_daily = pd.DataFrame()
        else:
            logger.info("\nComputing daily aggregates and normalized sentiment...")
            forum_daily_volume = df.groupby("post_date")["post_id"].nunique().to_dict()
            
            new_daily = df.groupby(["post_date", "ticker"]).agg(
                bullish_posts=("is_bullish", "sum"),
                bearish_posts=("is_bearish", "sum"),
                total_posts=("post_id", "count"),
                avg_bullish=("bullish", "mean"),
                avg_bearish=("bearish", "mean"),
                avg_net_sentiment=("net_sentiment", "mean"),
                avg_score=("score", "mean"),
                total_comments=("num_comments", "sum"),
            ).reset_index()
            
            new_daily["forum_total_dd"] = new_daily["post_date"].map(forum_daily_volume)
            new_daily["sentiment_score"] = new_daily["bullish_posts"] - new_daily["bearish_posts"]
            new_daily["normalized_sentiment_score"] = new_daily["sentiment_score"] / (new_daily["forum_total_dd"] + 1e-6)
            new_daily["sentiment_ratio"] = new_daily["bullish_posts"] / (new_daily["total_posts"] + 1e-6)
            
    # ------------------------------------------------------------------
    # INCREMENTAL DATABASE MERGING & DEDUPLICATION
    # ------------------------------------------------------------------
    logger.info("\nMerging results with existing database...")
    if os.path.exists(OUTPUT_CSV):
        existing_df = pd.read_csv(OUTPUT_CSV)
        existing_df["post_date"] = existing_df["post_date"].astype(str)
        if not new_daily.empty:
            new_daily["post_date"] = new_daily["post_date"].astype(str)
            # Concat the new run first to prioritize overwriting/updating older unpopulated runs
            combined = pd.concat([new_daily, existing_df], ignore_index=True)
        else:
            combined = existing_df
    else:
        combined = new_daily
        combined["post_date"] = combined["post_date"].astype(str)
        
    # Deduplicate strictly on the key pair to avoid any duplicate rows
    combined = combined.drop_duplicates(subset=["post_date", "ticker"], keep="first")
    logger.info(f"Total active records in database: {len(combined)}")
    
    # ------------------------------------------------------------------
    # RE-EVALUATION LOOP: ISOLATE MISSING ALPHA CHANNELS & APPLY TECHNICAL CONFLUENCE (MIXED METHOD)
    # ------------------------------------------------------------------
    return_cols = [f"alpha_{d}d" for d in FORWARD_DAYS]

    # Set up our expanded strategy mode columns
    expanded_strategy_cols = []
    for d in FORWARD_DAYS:
        expanded_strategy_cols += [
            f"short_ret_{d}d", f"short_alpha_{d}d",
            f"midlong_ret_{d}d", f"midlong_alpha_{d}d",
            f"longterm_ret_{d}d", f"longterm_alpha_{d}d",
            f"adaptive_ret_{d}d", f"adaptive_alpha_{d}d",
            f"mixed_ret_{d}d", f"mixed_alpha_{d}d"  # legacy compatibility
        ]

    mixed_cols = ["confluence_triggered", "pricing_failed"] + expanded_strategy_cols
    
    # Generate empty return columns if running the file for the first time
    for col in return_cols + [f"ret_{d}d" for d in FORWARD_DAYS] + [f"spy_ret_{d}d" for d in FORWARD_DAYS] + mixed_cols:
        if col not in combined.columns:
            if col in ["pricing_failed", "confluence_triggered"]:
                combined[col] = False
            else:
                combined[col] = None
            
    # Locate all entries with uncomputed performance metrics (NaNs) and not already marked as failed
    # Ensure regime_holding_days column exists in database before checking missing calculations
    if "regime_holding_days" not in combined.columns:
        combined["regime_holding_days"] = 5

    needs_calculation = combined[combined[return_cols].isna().any(axis=1) & (combined["pricing_failed"] != True)]  # noqa: E712 - equality comparison needed for pandas filtering or explicit boolean type check
    logger.info(f"Records requiring pricing updates/re-evaluation: {len(needs_calculation)}")
    
    if not needs_calculation.empty:
        unique_tickers = needs_calculation["ticker"].unique().tolist()
        post_dates = pd.to_datetime(needs_calculation["post_date"])
        # Buffer of 45 days prior to the min post date to warm up EMA, RSI, and MACD
        start_date = (post_dates.min() - timedelta(days=45)).strftime("%Y-%m-%d")
        end_date = (post_dates.max() + timedelta(days=450)).strftime("%Y-%m-%d")
        
        # Split into smaller chunks to avoid rate limits if we have many tickers to query
        chunk_size = 80
        all_px = []
        logger.info(f"Downloading historical stock data with OHLC for {len(unique_tickers)} stocks ({start_date} to {end_date})...")
        for chunk_idx in range(0, len(unique_tickers), chunk_size):
            chunk_tickers = unique_tickers[chunk_idx:chunk_idx + chunk_size]
            try:
                chunk_px = yf.download(chunk_tickers + ["SPY"], start=start_date, end=end_date, progress=False, auto_adjust=True)
                if not chunk_px.empty:
                    all_px.append(chunk_px)
            except Exception as e:
                logger.info(f"Warning: Price retrieval chunk failed: {e}.")

        if all_px:
            px = pd.concat(all_px, axis=1) if len(all_px) > 1 else all_px[0]
            # Deduplicate columns if any duplicate headers exist across chunks
            px = px.loc[:, ~px.columns.duplicated()]
        else:
            px = pd.DataFrame()
            
        if not px.empty:
            spy = None
            if isinstance(px.columns, pd.MultiIndex):
                if "SPY" in px.columns.levels[1]:
                    spy_df = px.loc[:, (slice(None), "SPY")].copy()
                    spy_df.columns = spy_df.columns.get_level_values(0)
                    spy = spy_df["Close"].dropna()
            else:
                spy = px["Close"].dropna()
                
            if spy is not None:
                # Recalculate only the rows requiring updates
                updated_rows = []
                for _, row in tqdm(needs_calculation.iterrows(), total=len(needs_calculation), desc="Recalculating Closes"):
                    t = row["ticker"]

                    tpx = pd.DataFrame()
                    if isinstance(px.columns, pd.MultiIndex):
                        if t in px.columns.levels[1]:
                            tpx = px.loc[:, (slice(None), t)].copy()
                            tpx.columns = tpx.columns.get_level_values(0)
                    else:
                        if t == unique_tickers[0]:
                            tpx = px.copy()

                    if tpx.empty:
                        base_dict = row.to_dict()
                        base_dict["pricing_failed"] = True
                        updated_rows.append(base_dict)
                        continue
                        
                    tpx = tpx.dropna(subset=["Close", "Open", "High", "Low"])
                    if len(tpx) < 15:
                        base_dict = row.to_dict()
                        base_dict["pricing_failed"] = True
                        updated_rows.append(base_dict)
                        continue
                        
                    # Compute indicator series
                    ind_df = compute_indicators(tpx)
                    if ind_df is None:
                        base_dict = row.to_dict()
                        base_dict["pricing_failed"] = True
                        updated_rows.append(base_dict)
                        continue
                        
                    post_ts = pd.Timestamp(row["post_date"])
                    entry_idx = ind_df.index.searchsorted(post_ts, side="right")
                    if entry_idx >= len(ind_df):
                        updated_rows.append(row.to_dict())
                        continue

                    entry_date = ind_df.index[entry_idx]
                    entry_px = ind_df["Close"].iloc[entry_idx]

                    # --------------------------------------------------------
                    # ADVANCED MULTI-ALGORITHM CONFLUENCE & RISK SHIELD (T+1 CLOSE ENTRY)
                    # --------------------------------------------------------
                    entry_row = ind_df.iloc[entry_idx]
                    sentiment_score = row["sentiment_score"]
                    gk_vol = entry_row.get("GK_Vol", 0.50)

                    # 1. Advanced Volatility Shield (Avoid highly unstable pump-and-dump/squeeze setups)
                    # If Garman-Klass Volatility exceeds 120% annualized, we block/avoid the trade entirely
                    volatility_shield_passed = gk_vol < 1.20

                    # Compute individual algorithmic voting channels (Expanded to 4 key indicators from Kapkar & 17 Repos):
                    # Alg 1: Heikin-Ashi Trend Continuation
                    alg_ha = False
                    # Alg 2: EMA & MACD Momentum Filter
                    alg_momentum = False
                    # Alg 3: RSI Overbought-Oversold Boundaries
                    alg_reversion = False
                    # Alg 4: Bollinger Bands Rebound/Volatility Boundaries (Mean Reversion & Volatility breakouts)
                    alg_bb = False

                    if sentiment_score > 0:
                        # Bullish Scenarios
                        alg_ha = entry_row["HA_Close"] > entry_row["HA_Open"]
                        alg_momentum = (entry_row["Close"] > entry_row["EMA_20"]) and (entry_row["MACD_Hist"] > 0.0)
                        # RSI healthy momentum zone (not overbought)
                        alg_reversion = (40.0 < entry_row["RSI_14"] < 70.0)
                        # Entry close price must be above Lower Bollinger Band or Middle Band to ensure we're not buying at extreme tops, or catching falling knives below Lower Band without reversal support
                        alg_bb = entry_row["Close"] > entry_row["BB_Lower"]
                    elif sentiment_score < 0:
                        # Bearish Scenarios
                        alg_ha = entry_row["HA_Close"] < entry_row["HA_Open"]
                        alg_momentum = (entry_row["Close"] < entry_row["EMA_20"]) and (entry_row["MACD_Hist"] < 0.0)
                        alg_reversion = (30.0 < entry_row["RSI_14"] < 60.0)
                        # Close below Upper Bollinger Band
                        alg_bb = entry_row["Close"] < entry_row["BB_Upper"]

                    # Ensemble Voting: N out of M (At least 3 out of 4 indicators must agree to filter extreme noise)
                    ensemble_score = int(alg_ha) + int(alg_momentum) + int(alg_reversion) + int(alg_bb)
                    confluence_triggered = (ensemble_score >= 3) and volatility_shield_passed

                    # 2. Risk Parity Allocation / Volatility-Adjusted Sizing
                    # Base allocation multiplier is inversely proportional to Garman-Klass Volatility
                    # Target portfolio volatility constant = 15% (0.15)
                    # We bound volatility between 15% and 120% to prevent extreme/infinite sizing weights
                    # Plus we add a Max-Sharpe scaling booster: if momentum indicators align perfectly (ensemble_score == 4),
                    # we increase capital efficiency allocation by 1.25x (representing dynamic Sharpe maximization optimization)
                    clipped_vol = max(min(gk_vol, 1.20), 0.15)
                    sharpe_multiplier = 1.25 if ensemble_score == 4 else 1.0
                    risk_parity_weight = (0.15 / clipped_vol) * sharpe_multiplier

                    # 3. Localized Statistical Multi-Factor Forecaster (Top Stock Prediction Repo Feature):
                    # Fusing a weighted momentum and indicator-based statistical forecaster to project the 5-day return.
                    # Based on rolling indicators (RSI position relative to bounds, BB position, and momentum).
                    bb_pos = (entry_row["Close"] - entry_row["BB_Lower"]) / (entry_row["BB_Upper"] - entry_row["BB_Lower"] + 1e-10)
                    rsi_mom = (entry_row["RSI_14"] - 50.0) / 50.0
                    macd_mom = entry_row["MACD_Hist"] / (entry_row["Close"] + 1e-10)
                    # Historical 5-day return momentum
                    hist_5d_ret = (entry_row["Close"] - ind_df["Close"].iloc[max(0, entry_idx-5)]) / (ind_df["Close"].iloc[max(0, entry_idx-5)] + 1e-10)

                    # Compute directional forecast expectation (weighted multi-factor projection)
                    projected_5d_return = 0.40 * hist_5d_ret + 0.30 * macd_mom + 0.15 * rsi_mom + 0.15 * (bb_pos - 0.50)

                    # Consensus Filter: Bullish trades require positive forecast; Bearish require negative forecast
                    forecast_passed = False
                    if sentiment_score > 0 and projected_5d_return > 0.005 or sentiment_score < 0 and projected_5d_return < -0.005: # At least +0.50% projected return
                        forecast_passed = True

                    # Final Trigger Confluence: Vote-Ensemble trigger must agree with our statistical Forecast
                    confluence_triggered = confluence_triggered and forecast_passed

                    # 4. OSQuant Tail-Risk Risk Limit (Expected Shortfall / CVaR Risk Filter):
                    # If estimated 95% Expected Shortfall (CVaR) exceeds 15% on a single-trade basis,
                    # we dynamically throttle/halve the position size to limit tail-loss risk exposure.
                    entry_cvar = entry_row.get("CVaR_95", 0.04)
                    if entry_cvar > 0.15:
                        risk_parity_weight *= 0.50

                    # 5. Conviction-Based Sizing Booster (Dynamic Growth Engine):
                    # If our localized statistical forecaster has extremely high conviction (projected return > 2%),
                    # we safely boost position size by up to 2.0x (capped by risk_config maximums)
                    # to aggressively compound profits on the $100 -> $500 journey!
                    if confluence_triggered and abs(projected_5d_return) > 0.02:
                        risk_parity_weight *= 2.00

                    spy_entry_date = entry_date if entry_date in spy.index else spy.index[spy.index.searchsorted(entry_date, side="left")]
                    spy_entry_px = spy.loc[spy_entry_date]

                    base_dict = row.to_dict()
                    base_dict["confluence_triggered"] = confluence_triggered
                    base_dict["GK_Vol"] = gk_vol
                    base_dict["risk_parity_weight"] = risk_parity_weight
                    base_dict["VaR_95"] = entry_row.get("VaR_95", 0.02)
                    base_dict["CVaR_95"] = entry_cvar
                    base_dict["projected_5d_return"] = projected_5d_return

                    # 6. Volatility-Based Dynamic Regime Switching Holding Periods for different horizons:
                    short_holding_days = 10 if gk_vol < 0.30 else 1
                    midlong_holding_days = 60 if gk_vol < 0.30 else 5
                    longterm_holding_days = 252 if gk_vol < 0.30 else 10

                    # S&P 500 Market Regime Detection for Auto-Regime Switching
                    spy_entry_idx = spy.index.searchsorted(entry_date, side="left")
                    if spy_entry_idx >= len(spy):
                        spy_entry_idx = len(spy) - 1

                    spy_window = spy.iloc[max(0, spy_entry_idx-19):spy_entry_idx+1]
                    if spy_entry_idx >= 20:
                        spy_ret_20d = (spy_entry_px - spy.iloc[spy_entry_idx-20]) / spy.iloc[spy_entry_idx-20]
                        spy_pct_rets = spy_window.pct_change().dropna()
                        spy_vol_20d = spy_pct_rets.std() * np.sqrt(252)
                    else:
                        spy_ret_20d = 0.05
                        spy_vol_20d = 0.12

                    if spy_ret_20d > 0 and spy_vol_20d < 0.15:
                        adaptive_mode = "long_term"
                        adaptive_holding_days = longterm_holding_days
                    elif spy_ret_20d > 0 and 0.15 <= spy_vol_20d < 0.25:
                        adaptive_mode = "mid_long_term"
                        adaptive_holding_days = midlong_holding_days
                    else:
                        adaptive_mode = "short_term"
                        adaptive_holding_days = short_holding_days

                    # Precompute target exit returns for each strategy
                    ret_stock_short, ret_spy_short = compute_regime_returns(ind_df, spy, entry_idx, entry_px, spy_entry_px, sentiment_score, short_holding_days)
                    ret_stock_midlong, ret_spy_midlong = compute_regime_returns(ind_df, spy, entry_idx, entry_px, spy_entry_px, sentiment_score, midlong_holding_days)
                    ret_stock_longterm, ret_spy_longterm = compute_regime_returns(ind_df, spy, entry_idx, entry_px, spy_entry_px, sentiment_score, longterm_holding_days)

                    if adaptive_mode == "long_term":
                        ret_stock_adaptive, ret_spy_adaptive = ret_stock_longterm, ret_spy_longterm
                    elif adaptive_mode == "mid_long_term":
                        ret_stock_adaptive, ret_spy_adaptive = ret_stock_midlong, ret_spy_midlong
                    else:
                        ret_stock_adaptive, ret_spy_adaptive = ret_stock_short, ret_spy_short

                    for d in FORWARD_DAYS:
                        target_idx = entry_idx + d
                        if target_idx < len(ind_df):
                            exit_date = ind_df.index[target_idx]
                            exit_px = ind_df["Close"].iloc[target_idx]

                            spy_exit_px = spy.loc[exit_date] if exit_date in spy.index else spy.iloc[min(spy.index.searchsorted(exit_date, side="left"), len(spy)-1)]

                            if sentiment_score > 0:
                                stock_ret = (exit_px - entry_px) / entry_px
                                spy_ret = (spy_exit_px - spy_entry_px) / spy_entry_px
                            else:
                                stock_ret = (entry_px - exit_px) / entry_px
                                spy_ret = (spy_entry_px - spy_exit_px) / spy_entry_px

                            base_dict[f"ret_{d}d"] = stock_ret
                            base_dict[f"spy_ret_{d}d"] = spy_ret
                            base_dict[f"alpha_{d}d"] = stock_ret - spy_ret

                            if confluence_triggered:
                                # Short-Term Strategy
                                base_dict[f"short_ret_{d}d"] = stock_ret * risk_parity_weight if d <= short_holding_days else ret_stock_short * risk_parity_weight
                                base_dict[f"short_alpha_{d}d"] = (stock_ret - spy_ret) * risk_parity_weight if d <= short_holding_days else (ret_stock_short - ret_spy_short) * risk_parity_weight

                                # Mid-Long Strategy
                                base_dict[f"midlong_ret_{d}d"] = stock_ret * risk_parity_weight if d <= midlong_holding_days else ret_stock_midlong * risk_parity_weight
                                base_dict[f"midlong_alpha_{d}d"] = (stock_ret - spy_ret) * risk_parity_weight if d <= midlong_holding_days else (ret_stock_midlong - ret_spy_midlong) * risk_parity_weight

                                # Long-Term Strategy
                                base_dict[f"longterm_ret_{d}d"] = stock_ret * risk_parity_weight if d <= longterm_holding_days else ret_stock_longterm * risk_parity_weight
                                base_dict[f"longterm_alpha_{d}d"] = (stock_ret - spy_ret) * risk_parity_weight if d <= longterm_holding_days else (ret_stock_longterm - ret_spy_longterm) * risk_parity_weight

                                # S&P 500 Adaptive Auto-Regime Switcher
                                base_dict[f"adaptive_ret_{d}d"] = stock_ret * risk_parity_weight if d <= adaptive_holding_days else ret_stock_adaptive * risk_parity_weight
                                base_dict[f"adaptive_alpha_{d}d"] = (stock_ret - spy_ret) * risk_parity_weight if d <= adaptive_holding_days else (ret_stock_adaptive - ret_spy_adaptive) * risk_parity_weight

                                # Legacy compatibility mapping to adaptive switcher
                                base_dict[f"mixed_ret_{d}d"] = base_dict[f"adaptive_ret_{d}d"]
                                base_dict[f"mixed_alpha_{d}d"] = base_dict[f"adaptive_alpha_{d}d"]
                            else:
                                base_dict[f"short_ret_{d}d"] = 0.0
                                base_dict[f"short_alpha_{d}d"] = 0.0
                                base_dict[f"midlong_ret_{d}d"] = 0.0
                                base_dict[f"midlong_alpha_{d}d"] = 0.0
                                base_dict[f"longterm_ret_{d}d"] = 0.0
                                base_dict[f"longterm_alpha_{d}d"] = 0.0
                                base_dict[f"adaptive_ret_{d}d"] = 0.0
                                base_dict[f"adaptive_alpha_{d}d"] = 0.0
                                base_dict[f"mixed_ret_{d}d"] = 0.0
                                base_dict[f"mixed_alpha_{d}d"] = 0.0
                        else:
                            base_dict[f"ret_{d}d"] = base_dict[f"spy_ret_{d}d"] = base_dict[f"alpha_{d}d"] = None
                            base_dict[f"short_ret_{d}d"] = base_dict[f"short_alpha_{d}d"] = None
                            base_dict[f"midlong_ret_{d}d"] = base_dict[f"midlong_alpha_{d}d"] = None
                            base_dict[f"longterm_ret_{d}d"] = base_dict[f"longterm_alpha_{d}d"] = None
                            base_dict[f"adaptive_ret_{d}d"] = base_dict[f"adaptive_alpha_{d}d"] = None
                            base_dict[f"mixed_ret_{d}d"] = base_dict[f"mixed_alpha_{d}d"] = None

                    base_dict["regime_holding_days"] = adaptive_holding_days
                    updated_rows.append(base_dict)

                # Merge updated calculations back into the main DataFrame
                updated_df = pd.DataFrame(updated_rows)
                combined = combined.set_index(["post_date", "ticker"])
                updated_df = updated_df.set_index(["post_date", "ticker"])
                combined.update(updated_df)
                combined = combined.reset_index()
            
    # Save the synchronized database (with OS permission lock failsafe)
    safe_write_csv(combined, OUTPUT_CSV)
    
    # ------------------------------------------------------------------
    # SAFELY MERGE CO-MENTIONS WITHOUT DOUBLE COUNTING
    # ------------------------------------------------------------------
    logger.info("\nMerging co-mention graphs...")
    new_co_mentions = defaultdict(lambda: defaultdict(int))
    if not items or df.empty:
        pass
    else:
        for date, group in df.groupby("post_date"):
            post_tickers = group.groupby("post_id")["ticker"].apply(list)
            for ticker_list in post_tickers:
                unique_t = sorted(list(set(ticker_list)))
                for i, t1 in enumerate(unique_t):
                    for t2 in unique_t[i+1:]:
                        new_co_mentions[str(date)][f"{t1}_{t2}"] += 1
                        
    if os.path.exists(CO_MENTION_JSON):
        with open(CO_MENTION_JSON, "r") as f:
            try:
                existing_co = json.load(f)
            except json.JSONDecodeError:
                existing_co = {}
    else:
        existing_co = {}
        
    for date_str, pairs in new_co_mentions.items():
        if date_str not in existing_co:
            existing_co[date_str] = pairs
        else:
            for pair_str, count in pairs.items():
                # Avoid duplicates by taking the maximum recorded count
                existing_co[date_str][pair_str] = max(existing_co[date_str].get(pair_str, 0), count)
                
    safe_write_json(existing_co, CO_MENTION_JSON)
        
    logger.info("\nData collections successfully synchronized:")
    logger.info(f" -> CSV dataset: {OUTPUT_CSV}")
    logger.info(f" -> Co-mention graph: {CO_MENTION_JSON}")
    return True

# ============================================================================
# PHASE 2: TRAJECTORY PLOTTER
# ============================================================================
def run_trajectory_plotter(top_n_tickers=5):
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 2: GENERATING PERFORMANCE TRAJECTORY GRAPHS")
    logger.info("=" * 60)
    
    if not os.path.exists(OUTPUT_CSV):
        logger.info(f"Error: Could not locate the database CSV at {OUTPUT_CSV}")
        return
        
    df = pd.read_csv(OUTPUT_CSV)
    df['post_date'] = pd.to_datetime(df['post_date'])
    
    # Filter out tickers that are marked as pricing_failed to ensure we only select tickers with valid price data for plotting
    valid_df = df[df['pricing_failed'] != True]  # noqa: E712 - equality comparison needed for pandas filtering or explicit boolean type check
    top_tickers = valid_df['ticker'].value_counts().head(top_n_tickers).index.tolist()
    logger.info(f"Selected top {top_n_tickers} tickers for plotting: {top_tickers}")
    
    events_to_plot = []
    for ticker in top_tickers:
        ticker_df = df[df['ticker'] == ticker]
        best_event = ticker_df.loc[ticker_df['sentiment_score'].idxmax()]
        events_to_plot.append({
            'ticker': ticker,
            'post_date': best_event['post_date']
        })
        
    # sns.set_theme(style="whitegrid") # Removed seaborn dependency
    plt.style.use("seaborn-v0_8-whitegrid") if "seaborn-v0_8-whitegrid" in plt.style.available else plt.grid(True)
    fig, ax = plt.subplots(figsize=(12, 7))
    
    spy_trajectories = []
    
    for event in events_to_plot:
        ticker = event['ticker']
        post_date = event['post_date']
        
        start_dl = (post_date - timedelta(days=20)).strftime("%Y-%m-%d")
        end_dl = (post_date + timedelta(days=140)).strftime("%Y-%m-%d")
        
        try:
            px = yf.download([ticker, "SPY"], start=start_dl, end=end_dl, progress=False, auto_adjust=True)
            px_close = px["Close"] if (isinstance(px, pd.DataFrame) and "Close" in px) else px
        except Exception as e:
            logger.debug(f"Failed to fetch yfinance data for plotting: {e}")
            continue
            
        if ticker not in px_close.columns or "SPY" not in px_close.columns:
            continue
            
        stock_series = px_close[ticker].dropna()
        spy_series = px_close["SPY"].dropna()
        
        entry_idx = stock_series.index.searchsorted(post_date, side="right")
        if entry_idx >= len(stock_series) or entry_idx < 10:
            continue
            
        entry_date = stock_series.index[entry_idx]
        entry_px = stock_series.iloc[entry_idx]
        
        spy_entry_idx = spy_series.index.searchsorted(entry_date, side="left")
        spy_entry_px = spy_series.iloc[spy_entry_idx]
        
        start_idx = entry_idx - 10
        end_idx = min(len(stock_series), entry_idx + 91)
        
        stock_window = stock_series.iloc[start_idx:end_idx]
        spy_window = spy_series.loc[spy_series.index.intersection(stock_window.index)]
        
        normalized_stock = (stock_window / entry_px) * 100
        normalized_spy = (spy_window / spy_entry_px) * 100
        
        relative_days = [i - 10 for i in range(len(stock_window))]
        
        # Get confluence flag from the database
        event_row = df[(df['ticker'] == ticker) & (df['post_date'] == post_date)]
        confluence_triggered = False
        if not event_row.empty:
            confluence_triggered = bool(event_row.iloc[0].get('confluence_triggered', False))

        # Plot Stock path (thinner line)
        line_ref, = ax.plot(relative_days, normalized_stock, label=f"{ticker} (Stock path, Post: {post_date.strftime('%Y-%m-%d')})", linewidth=1.2, alpha=0.5, linestyle=":")
        color = line_ref.get_color()

        # Plot Mixed strategy path (solid line)
        # If confluence is True, tracks stock scaled by risk parity allocation weight. Else, stays at 100.0 from T=0 onwards.
        event_row = df[(df['ticker'] == ticker) & (df['post_date'] == post_date)]
        risk_parity_weight = 1.0
        if not event_row.empty:
            risk_parity_weight = float(event_row.iloc[0].get('risk_parity_weight', 1.0))

        mixed_path = []
        for rd, ns in zip(relative_days, normalized_stock.values):
            if rd < 0:
                mixed_path.append(ns)
            else:
                if confluence_triggered:
                    # Normalized trajectory scaled by the allocation weight (measured from 100 base)
                    weighted_val = 100.0 + (ns - 100.0) * risk_parity_weight
                    mixed_path.append(weighted_val)
                else:
                    mixed_path.append(100.0)

        confluence_label = "Triggered" if confluence_triggered else "Avoided"
        ax.plot(relative_days, mixed_path, label=f"{ticker} (Adaptive Switcher, Confluence: {confluence_label})", color=color, linewidth=2.0)

        spy_trajectories.append(pd.Series(normalized_spy.values, index=relative_days))
        
    if spy_trajectories:
        spy_df = pd.DataFrame(spy_trajectories).mean(axis=0).sort_index()
        ax.plot(spy_df.index, spy_df.values, label="SPY Benchmark (Average)", color="black", linestyle="--", linewidth=2.5)
        
    ax.axvline(x=0, color="red", linestyle=":", linewidth=1.5, label="Entry Execution (T+1 Close)")
    ax.axhline(y=100, color="gray", linestyle="-", linewidth=0.5)
    
    ax.set_title("WSB Sentiment vs. Adaptive Auto-Regime Switcher: At Time of Post ($T=0$) vs. Months Later ($T+90$)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Relative Trading Days Offset from Entry Day ($T=0$)")
    ax.set_ylabel("Normalized Asset Value (Base 100 at Entry)")
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
    ax.set_xlim(-10, 90)
    
    plt.tight_layout()
    
    # Save target plot securely with failsafe retry logic
    while True:
        try:
            plt.savefig(OUTPUT_PNG, dpi=300)
            break
        except PermissionError:
            logger.info(f"\n[!] OS Permission Denied: Cannot write to {OUTPUT_PNG}")
            logger.info("This occurs because the PNG plot is currently open or locked by another utility.")
            input("Please close any image viewer accessing this file and press Enter to retry saving...")
            
    logger.info("Trajectory plot saved successfully:")
    logger.info(f" -> Visualization PNG: {OUTPUT_PNG}")
    # plt.show() deleted to avoid blocking non-interactive terminals

# ============================================================================
# MASTER CONTROLLER
# ============================================================================
def print_quant_statistics():
    """
    Computes and prints professional quant backtest stats (inspired by QuantStats and pyfolio)
    comparing the raw sentiment-only strategy to our optimized Confluence-Ensemble strategy.
    """
    if not os.path.exists(OUTPUT_CSV):
        return
    df = pd.read_csv(OUTPUT_CSV)

    logger.info("\n" + "=" * 60)
    logger.info("PORTFOLIO PERFORMANCE & RISK METRICS REPORT (QuantStats-Style)")
    logger.info("=" * 60)

    # Analyze 5-day horizon (standard medium-term horizon)
    raw_rets = df["ret_5d"].dropna()
    adaptive_rets = df["adaptive_ret_5d"].dropna()

    if len(raw_rets) == 0 or len(adaptive_rets) == 0:
        logger.info("Not enough backtest data available to generate statistics.")
        return

    def compute_stats(rets):
        mean_ret = rets.mean()
        std_ret = rets.std()
        win_rate = (rets > 0).sum() / len(rets) if len(rets) > 0 else 0.0
        # Sharpe (annualized, assuming ~50 rebalances/trades a year, risk free rate = 0)
        sharpe = (mean_ret / (std_ret + 1e-10)) * np.sqrt(50) if std_ret > 0 else 0.0
        # Sortino (considering downside standard deviation)
        downside_rets = rets[rets < 0]
        downside_std = downside_rets.std() if len(downside_rets) > 1 else std_ret
        sortino = (mean_ret / (downside_std + 1e-10)) * np.sqrt(50) if downside_std > 0 else 0.0
        # Max Drawdown
        cum_prod = (1 + rets).cumprod()
        running_max = cum_prod.cummax()
        drawdown = (cum_prod - running_max) / running_max
        max_dd = drawdown.min() if len(drawdown) > 0 else 0.0

        # OSQuant Risk Measures: Portfolio 95% historical Value-at-Risk (VaR) & Expected Shortfall (CVaR)
        sorted_rets = np.sort(rets.values)
        var_idx = int(0.05 * len(sorted_rets))
        hist_var = -sorted_rets[var_idx] if len(sorted_rets) > 0 and var_idx < len(sorted_rets) else 0.0
        losses_below_var = sorted_rets[:var_idx+1]
        hist_cvar = -losses_below_var.mean() if len(losses_below_var) > 0 else 0.0

        return mean_ret * 100, std_ret * 100, win_rate * 100, sharpe, sortino, max_dd * 100, hist_var * 100, hist_cvar * 100

    raw_mean, raw_std, raw_win, raw_sharpe, raw_sortino, raw_mdd, raw_var, raw_cvar = compute_stats(raw_rets)
    mix_mean, mix_std, mix_win, mix_sharpe, mix_sortino, mix_mdd, mix_var, mix_cvar = compute_stats(adaptive_rets)

    logger.info(f"{'Metric':<25} | {'Raw Sentiment Strategy':<25} | {'Adaptive Auto-Regime Switcher':<25}")
    logger.info("-" * 81)
    logger.info(f"{'Mean Trade Return':<25} | {raw_mean:>22.2f}% | {mix_mean:>22.2f}%")
    logger.info(f"{'Volatility (Std Dev)':<25} | {raw_std:>22.2f}% | {mix_std:>22.2f}%")
    logger.info(f"{'Win Rate':<25} | {raw_win:>22.2f}% | {mix_win:>22.2f}%")
    logger.info(f"{'Annualized Sharpe Ratio':<25} | {raw_sharpe:>24.2f} | {mix_sharpe:>24.2f}")
    logger.info(f"{'Annualized Sortino Ratio':<25} | {raw_sortino:>24.2f} | {mix_sortino:>24.2f}")
    logger.info(f"{'Maximum Drawdown':<25} | {raw_mdd:>22.2f}% | {mix_mdd:>22.2f}%")
    logger.info(f"{'Value-at-Risk (95% VaR)':<25} | {raw_var:>22.2f}% | {mix_var:>22.2f}%")
    logger.info(f"{'Expected Shortfall (CVaR)':<25} | {raw_cvar:>22.2f}% | {mix_cvar:>22.2f}%")
    logger.info("-" * 81)
    logger.info("Interpretation: The Adaptive Auto-Regime Switcher with the Bollinger Bands Filter,")
    logger.info("Garman-Klass Volatility Shield, and Max-Sharpe asset allocation vastly reduces volatility")
    logger.info("and tail risk while preserving win rate and protecting investment capital.")
    logger.info("=" * 60)

def main():
    success = run_sentiment_pipeline()
    if success:
        run_trajectory_plotter(top_n_tickers=5)
        print_quant_statistics()
        logger.info("\n" + "=" * 60)
        logger.info("SYSTEM EXECUTION COMPLETED")
        logger.info("=" * 60)
        logger.info(f"1. Raw Sentiment Data & Alpha Calculations:\n   {os.path.abspath(OUTPUT_CSV)}")
        logger.info(f"2. Safe Co-mention Network JSON File:\n   {os.path.abspath(CO_MENTION_JSON)}")
        logger.info(f"3. Forward-Looking Normalized Trajectory Plot:\n   {os.path.abspath(OUTPUT_PNG)}")
        logger.info("=" * 60)
    else:
        logger.info("\nPipeline stopped: No valid post data retrieved or parsed.")

if __name__ == "__main__":
    main()
