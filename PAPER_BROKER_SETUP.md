# Paper Broker Configuration Guide

This guide explains how to configure the WSB-Alpha-System's execution bridge to securely interface with open-source paper trading infrastructure (like `paperbroker`) and enable Discord/Telegram webhooks for daily summaries.

## 1. Create your `.env` File
In the root directory of the repository, create a file named `.env`. The system uses the `python-dotenv` package to load these credentials dynamically and securely into the environment without hardcoding them in the source code.

## 2. Required Variables
Add the following variables to your `.env` file:

```env
# ==========================================
# WSB-ALPHA-SYSTEM CONFIGURATION
# ==========================================

# 1. APIFY Token (Required for the Reddit scraper)
APIFY_TOKEN=your_apify_token_here

# ==========================================
# PAPER TRADING EXECUTION (PAPERBROKER)
# ==========================================
# The base URL where your paperbroker instance is running.
# If running locally, it is usually http://localhost:5000
PAPERBROKER_URL=http://localhost:5000

# The API key required to authenticate with the paperbroker instance.
# Leave blank if authentication is disabled on the broker.
PAPERBROKER_API_KEY=your_paperbroker_api_key_here

# ==========================================
# NOTIFICATIONS / WEBHOOKS
# ==========================================
# A Discord or Telegram Webhook URL to receive a daily summary of executed trades.
# E.g. https://discord.com/api/webhooks/1234567890/ABCDEFG
DISCORD_WEBHOOK_URL=your_discord_webhook_url_here
```

## 3. Webhook Setup
To set up a Discord webhook:
1. Open your Discord server.
2. Go to `Server Settings` -> `Integrations` -> `Webhooks`.
3. Click `New Webhook`, give it a name (e.g. "WSB-Quant-Bot"), and select the channel.
4. Click `Copy Webhook URL` and paste it into the `DISCORD_WEBHOOK_URL` field in your `.env` file.

## 4. Scheduling the Live Trading Orchestrator
To run the automated trading pipeline exactly 15 minutes before the market close (3:45 PM EST) automatically, configure a cron job on your server.

Open your crontab editor:
```bash
crontab -e
```

Add the following entry (assuming your server runs on EST time, and using a virtual environment):
```bash
# Run main_live.py every Monday through Friday at 15:45 (3:45 PM)
45 15 * * 1-5 cd /path/to/WSB-Alpha-System && /path/to/venv/bin/python main_live.py >> cron_execution.log 2>&1
```
