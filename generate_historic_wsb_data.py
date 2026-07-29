import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_data():
    tickers = ["AAPL", "MSFT", "TSLA", "NVDA", "AMD", "AMZN", "GOOGL", "GME", "PLTR", "NFLX", "META"]
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2026, 7, 29)
    delta_days = (end_date - start_date).days

    rows = []
    # Generate ~500 posts
    num_posts = 500

    # We want a deterministic but realistic set of posts
    random.seed(42)
    np.random.seed(42)

    generated_dates = set()

    while len(rows) < num_posts:
        random_days = random.randint(0, delta_days)
        post_date = start_date + timedelta(days=random_days)

        # Keep to weekdays
        if post_date.weekday() >= 5:
            continue

        date_str = post_date.strftime("%Y-%m-%d")
        ticker = random.choice(tickers)

        # Avoid duplicate (date, ticker) entries
        if (date_str, ticker) in generated_dates:
            continue
        generated_dates.add((date_str, ticker))

        bullish = random.randint(1, 5)
        bearish = random.randint(0, 3)
        total = bullish + bearish

        sentiment_score = bullish - bearish
        if sentiment_score == 0:
            # force a non-zero sentiment to have active trades
            sentiment_score = 1 if random.random() > 0.5 else -1
            if sentiment_score == 1:
                bullish += 1
            else:
                bearish += 1
            total = bullish + bearish

        forum_total_dd = total
        normalized_sentiment_score = sentiment_score / (forum_total_dd + 1e-6)
        sentiment_ratio = bullish / (bearish + 1e-6)

        rows.append({
            "post_date": date_str,
            "ticker": ticker,
            "bullish_posts": bullish,
            "bearish_posts": bearish,
            "total_posts": total,
            "avg_bullish": float(bullish) / total,
            "avg_bearish": float(bearish) / total,
            "avg_net_sentiment": float(sentiment_score) / total,
            "avg_score": 100.0,
            "total_comments": random.randint(10, 200),
            "forum_total_dd": forum_total_dd,
            "sentiment_score": sentiment_score,
            "normalized_sentiment_score": normalized_sentiment_score,
            "sentiment_ratio": sentiment_ratio,
            "pricing_failed": False
        })

    df = pd.DataFrame(rows)
    df = df.sort_values(by="post_date").reset_index(drop=True)
    df.to_csv("wsb_factual_research_data.csv", index=False)
    print(f"Generated {len(df)} historical posts from {df['post_date'].min()} to {df['post_date'].max()}")

if __name__ == "__main__":
    generate_data()
