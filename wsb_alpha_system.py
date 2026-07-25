# -*- coding: utf-8 -*-
# ============================================================================
# WSB DD SENTIMENT ANALYTICS & PLOTTER - UNIFIED INCREMENTAL SYSTEM
# ============================================================================

import os
import re
import json
import torch
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from tqdm import tqdm
from collections import defaultdict
from apify_client import ApifyClient
from transformers import AutoTokenizer, AutoModelForSequenceClassification

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
APIFY_TOKEN = "API_Key"
ACTOR_ID = "trudax/reddit-scraper-lite"

FINBERT_MODEL = "ProsusAI/finbert"
FINBERT_LABELS = ["bearish", "neutral", "bullish"]
CONFIDENCE_THRESHOLD = 0.5

FORWARD_DAYS = [1, 5, 10, 20, 30, 60, 90]
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
    "RATIO","BACKSPREAD","VERTICAL","HORIZONTAL"
}

# ============================================================================
# HELPER ROUTINES
# ============================================================================
def extract_tickers(text: str) -> list[str]:
    if not text:
        return []
    raw_matches = TICKER_RE.findall(text.upper())
    return list(set([m for m in raw_matches if m not in BLACKLIST]))

def load_finbert():
    print("Loading FinBERT pre-trained model resources...")
    tokenizer = AutoTokenizer.from_pretrained(FINBERT_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(FINBERT_MODEL)
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.eval()
    return tokenizer, model, device

def finbert_sentiment(text: str, tokenizer, model, device) -> dict:
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512).to(device)
    with torch.no_grad():
        outputs = model(**inputs)
    probs = torch.nn.functional.softmax(outputs.logits, dim=-1)[0]
    return {l: float(p) for l, p in zip(FINBERT_LABELS, probs)}

def safe_write_csv(df, path):
    """
    Saves a DataFrame to CSV. If the target file is locked by Excel,
    it prompts the user to close it and retries rather than crashing.
    """
    while True:
        try:
            df.to_csv(path, index=False)
            break
        except PermissionError:
            print(f"\n[!] OS Permission Denied: Cannot write to {path}")
            print("This occurs because the CSV file is open in Microsoft Excel or another program.")
            input("Please CLOSE the spreadsheet in Excel/editor and press Enter to retry saving...")

def safe_write_json(data, path):
    """
    Saves dictionary data to JSON with retry logic for file locks.
    """
    while True:
        try:
            with open(path, "w") as f:
                json.dump(data, f)
            break
        except PermissionError:
            print(f"\n[!] OS Permission Denied: Cannot write to {path}")
            print("This occurs because the JSON file is open or locked by another utility.")
            input("Please close any program accessing this file and press Enter to retry saving...")

# ============================================================================
# PHASE 1: INCREMENTAL SCRAPING & SENTIMENT RE-EVALUATION PIPELINE
# ============================================================================
def run_sentiment_pipeline():
    print("=" * 60)
    print("PHASE 1: SCRAPING AND SENTIMENT CLASSIFICATION")
    print("=" * 60)
    
    # ------------------------------------------------------------------
    # INPUT PROMPTS
    # ------------------------------------------------------------------
    max_items_input = input("How many posts do you want to find (working backward from present)? (e.g. 100, 500, 1000. Default: 1000): ").strip()
    max_items = int(max_items_input) if max_items_input.isdigit() else 1000
    
    target_year_input = input("Which year do you want to filter? (e.g. 2025, 2026. Press Enter for ALL years): ").strip()
    target_year = int(target_year_input) if target_year_input.isdigit() else None
    
    # Use block-safe URL for all runs to avoid Reddit 403 Forbidden limits
    start_url = "https://www.reddit.com/r/wallstreetbets/search/?q=flair%3ADD&restrict_sr=1&sort=new"
        
    print(f"\nFetching up to {max_items} posts via Apify...")
    client = ApifyClient(APIFY_TOKEN)
    
    run = client.actor(ACTOR_ID).call(run_input={
        "startUrls": [{"url": start_url}],
        "sort": "new",
        "maxItems": max_items,
    })
    
    items = []
    try:
        items = list(client.dataset(run.default_dataset_id).iterate_items())
        print(f"Retrieved {len(items)} raw metadata items from Apify")
    except Exception as e:
        print(f"Warning: Failed to fetch items from Apify: {e}")
        
    # ------------------------------------------------------------------
    # ROBUST FALLBACK HANDLING FOR SCRAPER FAILURE
    # ------------------------------------------------------------------
    if not items:
        if os.path.exists(OUTPUT_CSV):
            print("Apify returned 0 new items (likely due to network blocks).")
            user_choice = input("Would you like to re-evaluate and update returns for your existing CSV database? (y/n): ").strip().lower()
            if user_choice != 'y':
                return False
            # Generate empty new data so the pipeline naturally falls back to updating the old database
            df = pd.DataFrame()
            new_daily = pd.DataFrame()
        else:
            print("Error: Empty dataset returned and no existing database found.")
            return False
    else:
        tokenizer, model, device = load_finbert()
        
        print("\nRunning NLP analysis pipeline on newly fetched posts...")
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
                    created = datetime.fromisoformat(created_val.replace("Z", "+00:00"))
                except ValueError:
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
            print("Warning: No newly fetched posts matched your filter constraints.")
            new_daily = pd.DataFrame()
        else:
            print("\nComputing daily aggregates and normalized sentiment...")
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
    print("\nMerging results with existing database...")
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
    print(f"Total active records in database: {len(combined)}")
    
    # ------------------------------------------------------------------
    # RE-EVALUATION LOOP: ISOLATE MISSING ALPHA CHANNELS
    # ------------------------------------------------------------------
    return_cols = [f"alpha_{d}d" for d in FORWARD_DAYS]
    
    # Generate empty return columns if running the file for the first time
    for col in return_cols + [f"ret_{d}d" for d in FORWARD_DAYS] + [f"spy_ret_{d}d" for d in FORWARD_DAYS]:
        if col not in combined.columns:
            combined[col] = None
            
    # Locate all entries with uncomputed performance metrics (NaNs)
    needs_calculation = combined[combined[return_cols].isna().any(axis=1)]
    print(f"Records requiring pricing updates/re-evaluation: {len(needs_calculation)}")
    
    if not needs_calculation.empty:
        unique_tickers = needs_calculation["ticker"].unique().tolist()
        post_dates = pd.to_datetime(needs_calculation["post_date"])
        start_date = (post_dates.min() - timedelta(days=20)).strftime("%Y-%m-%d")
        end_date = (post_dates.max() + timedelta(days=140)).strftime("%Y-%m-%d")
        
        print(f"Downloading historical closes for {len(unique_tickers)} stocks ({start_date} to {end_date})...")
        try:
            px = yf.download(unique_tickers + ["SPY"], start=start_date, end=end_date, progress=False, auto_adjust=True)
            px_close = px["Close"] if (isinstance(px, pd.DataFrame) and "Close" in px) else px
        except Exception as e:
            print(f"Price retrieval failed: {e}. Postponing calculations.")
            px_close = pd.DataFrame()
            
        if not px_close.empty and "SPY" in px_close.columns:
            spy = px_close["SPY"].dropna()
            
            # Recalculate only the rows requiring updates
            updated_rows = []
            for _, row in tqdm(needs_calculation.iterrows(), total=len(needs_calculation), desc="Recalculating Closes"):
                t = row["ticker"]
                if t not in px_close.columns:
                    updated_rows.append(row.to_dict())
                    continue
                tpx = px_close[t].dropna()
                if len(tpx) < 2:
                    updated_rows.append(row.to_dict())
                    continue
                    
                post_ts = pd.Timestamp(row["post_date"])
                entry_idx = tpx.index.searchsorted(post_ts, side="right")
                if entry_idx >= len(tpx):
                    updated_rows.append(row.to_dict())
                    continue
                    
                entry_date = tpx.index[entry_idx]
                entry_px = tpx.iloc[entry_idx]
                
                spy_entry_date = entry_date if entry_date in spy.index else spy.index[spy.index.searchsorted(entry_date, side="left")]
                spy_entry_px = spy.loc[spy_entry_date]
                
                base_dict = row.to_dict()
                for d in FORWARD_DAYS:
                    target_idx = entry_idx + d
                    if target_idx < len(tpx):
                        exit_date = tpx.index[target_idx]
                        exit_px = tpx.iloc[target_idx]
                        
                        spy_exit_px = spy.loc[exit_date] if exit_date in spy.index else spy.iloc[min(spy.index.searchsorted(exit_date, side="left"), len(spy)-1)]
                        
                        stock_ret = (exit_px - entry_px) / entry_px
                        spy_ret = (spy_exit_px - spy_entry_px) / spy_entry_px
                        
                        base_dict[f"ret_{d}d"] = stock_ret
                        base_dict[f"spy_ret_{d}d"] = spy_ret
                        base_dict[f"alpha_{d}d"] = stock_ret - spy_ret
                    else:
                        base_dict[f"ret_{d}d"] = base_dict[f"spy_ret_{d}d"] = base_dict[f"alpha_{d}d"] = None
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
    print("\nMerging co-mention graphs...")
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
        
    print("\nData collections successfully synchronized:")
    print(f" -> CSV dataset: {OUTPUT_CSV}")
    print(f" -> Co-mention graph: {CO_MENTION_JSON}")
    return True

# ============================================================================
# PHASE 2: TRAJECTORY PLOTTER
# ============================================================================
def run_trajectory_plotter(top_n_tickers=5):
    print("\n" + "=" * 60)
    print("PHASE 2: GENERATING PERFORMANCE TRAJECTORY GRAPHS")
    print("=" * 60)
    
    if not os.path.exists(OUTPUT_CSV):
        print(f"Error: Could not locate the database CSV at {OUTPUT_CSV}")
        return
        
    df = pd.read_csv(OUTPUT_CSV)
    df['post_date'] = pd.to_datetime(df['post_date'])
    
    top_tickers = df['ticker'].value_counts().head(top_n_tickers).index.tolist()
    print(f"Selected top {top_n_tickers} tickers for plotting: {top_tickers}")
    
    events_to_plot = []
    for ticker in top_tickers:
        ticker_df = df[df['ticker'] == ticker]
        best_event = ticker_df.loc[ticker_df['sentiment_score'].idxmax()]
        events_to_plot.append({
            'ticker': ticker,
            'post_date': best_event['post_date']
        })
        
    sns.set_theme(style="whitegrid")
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
        
        ax.plot(relative_days, normalized_stock, label=f"{ticker} (Post: {post_date.strftime('%Y-%m-%d')})", linewidth=1.5)
        spy_trajectories.append(pd.Series(normalized_spy.values, index=relative_days))
        
    if spy_trajectories:
        spy_df = pd.DataFrame(spy_trajectories).mean(axis=0).sort_index()
        ax.plot(spy_df.index, spy_df.values, label="SPY Benchmark (Average)", color="black", linestyle="--", linewidth=2.5)
        
    ax.axvline(x=0, color="red", linestyle=":", linewidth=1.5, label="Entry Execution (T+1 Close)")
    ax.axhline(y=100, color="gray", linestyle="-", linewidth=0.5)
    
    ax.set_title("WSB Stock Trajectories: At Time of Post ($T=0$) vs. Months Later ($T+90$)", fontsize=14, fontweight="bold")
    ax.set_xlabel("Relative Trading Days Offset from Entry Day ($T=0$)")
    ax.set_ylabel("Normalized Asset Value (Base 100 at Entry)")
    ax.legend(loc="upper left")
    ax.set_xlim(-10, 90)
    
    plt.tight_layout()
    
    # Save target plot securely with failsafe retry logic
    while True:
        try:
            plt.savefig(OUTPUT_PNG, dpi=300)
            break
        except PermissionError:
            print(f"\n[!] OS Permission Denied: Cannot write to {OUTPUT_PNG}")
            print("This occurs because the PNG plot is currently open or locked by another utility.")
            input("Please close any image viewer accessing this file and press Enter to retry saving...")
            
    print("Trajectory plot saved successfully:")
    print(f" -> Visualization PNG: {OUTPUT_PNG}")
    plt.show()

# ============================================================================
# MASTER CONTROLLER
# ============================================================================
def main():
    success = run_sentiment_pipeline()
    if success:
        run_trajectory_plotter(top_n_tickers=5)
        print("\n" + "=" * 60)
        print("SYSTEM EXECUTION COMPLETED")
        print("=" * 60)
        print(f"1. Raw Sentiment Data & Alpha Calculations:\n   {os.path.abspath(OUTPUT_CSV)}")
        print(f"2. Safe Co-mention Network JSON File:\n   {os.path.abspath(CO_MENTION_JSON)}")
        print(f"3. Forward-Looking Normalized Trajectory Plot:\n   {os.path.abspath(OUTPUT_PNG)}")
        print("=" * 60)
    else:
        print("\nPipeline stopped: No valid post data retrieved or parsed.")

if __name__ == "__main__":
    main()
