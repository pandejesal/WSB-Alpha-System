import os
import random
import sqlite3
from datetime import datetime, timedelta, timezone

import yaml


def create_trades_db():
    if os.path.exists("trades.db"):
        os.remove("trades.db")

    conn = sqlite3.connect("trades.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,
            direction TEXT,
            entry_time TEXT,
            exit_time TEXT,
            entry_price REAL,
            exit_price REAL,
            pnl_percent REAL,
            mfe_percent REAL,
            mae_percent REAL,
            strategy_id TEXT
        )
    """)

    tickers = ["AAPL", "MSFT", "GOOG", "TSLA", "META"]
    directions = ["LONG", "SHORT"]
    strategy_id = "alpha_fusion_v1"

    base_time = datetime.now(timezone.utc) - timedelta(days=60)

    trades = []
    for i in range(50):
        ticker = random.choice(tickers)
        direction = random.choice(directions)
        entry_time = base_time + timedelta(days=i, hours=random.randint(1, 4))
        exit_time = entry_time + timedelta(days=random.randint(1, 3))

        entry_price = random.uniform(100, 200)

        # Simulate realistic PNL, MFE, MAE
        pnl_percent = random.normalvariate(0.005, 0.02)

        if pnl_percent > 0:
            mfe_percent = pnl_percent + abs(random.normalvariate(0.01, 0.005))
            mae_percent = -abs(random.normalvariate(0.005, 0.005))
        else:
            mfe_percent = abs(random.normalvariate(0.005, 0.005))
            mae_percent = pnl_percent - abs(random.normalvariate(0.01, 0.005))

        if direction == "LONG":
            exit_price = entry_price * (1 + pnl_percent)
        else:
            exit_price = entry_price * (1 - pnl_percent)

        trades.append((
            ticker,
            direction,
            entry_time.isoformat(),
            exit_time.isoformat(),
            round(entry_price, 2),
            round(exit_price, 2),
            round(pnl_percent, 4),
            round(mfe_percent, 4),
            round(mae_percent, 4),
            strategy_id
        ))

    cursor.executemany("""
        INSERT INTO trades (ticker, direction, entry_time, exit_time, entry_price, exit_price, pnl_percent, mfe_percent, mae_percent, strategy_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, trades)

    conn.commit()
    conn.close()
    print("Created mock trades.db with 50 trades.")

def create_strategy_config():
    config = {
        "strategy_name": "Alpha Fusion Confluence",
        "version": "1.0.0",
        "parameters": {
            "cvar_threshold": 0.15,
            "stop_loss_atr": 1.5,
            "take_profit_atr": 2.0,
            "ema_fast": 10,
            "ema_slow": 21,
            "macd_fast": 12,
            "macd_slow": 26,
            "macd_signal": 9
        },
        "risk_management": {
            "max_risk_per_trade_usd": 1.00,
            "account_balance_usd": 100.00
        }
    }

    with open("strategy_config.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    print("Created mock strategy_config.yaml.")

if __name__ == "__main__":
    create_trades_db()
    create_strategy_config()
