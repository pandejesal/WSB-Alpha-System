# 🤖 Automated Trading Deployment Guide: WSB Sentiment with Technical Confluence

This guide outlines a professional, production-grade cloud architecture to automate our Retail Sentiment with Technical Confluence strategy. By deploying this system in the cloud, you can scrape reddit posts, analyze sentiment, run indicator confluence checks, size positions, and execute trades in paper or live accounts—completely hands-free.

---

## 🏗️ 1. Automated System Architecture

The automation pipeline consists of five decoupled layers executing sequentially:

```
[Trigger: Cron / CloudWatch]
       │
       ▼
1. DATA INGESTION: Scrapes latest WSB DD posts (Free Public RSS / Paid Apify Scraper)
       │
       ▼
2. SENTIMENT CLASSIFICATION: Runs FinBERT NLP model to extract bullish/bearish confidence
       │
       ▼
3. QUANT CONFLUENCE: Computes Indicators (Heikin-Ashi, EMA, RSI, MACD, BB) & SPY Market Regime
       │
       ▼
4. RISK SIZING: Computes Risk Parity weighting & dynamic holding period based on GK Volatility
       │
       ▼
5. LIVE EXECUTION: Places Buy/Sell market orders via Broker API (Alpaca / Interactive Brokers)
```

---

## ☁️ 2. Cloud Infrastructure Options

### Option A: AWS EC2 / GCP Compute Engine (Easiest & Most Robust)
Deploying the pipeline on a small virtual machine (such as an AWS `t3.medium` with at least 4GB RAM to load the FinBERT PyTorch model) is the most straightforward method.

1. **Spin up a Linux VM** (Ubuntu 22.04 LTS).
2. **Install system dependencies**:
   ```bash
   sudo apt-get update && sudo apt-get install -y python3-pip git
   ```
3. **Clone the repository and install requirements**:
   ```bash
   git clone https://github.com/pandejesal/WSB-Alpha-System.git /app
   cd /app
   pip install -r requirements.txt
   ```
4. **Configure Secrets**: Create a `.env` file containing broker API credentials and scraper tokens.

### Option B: AWS Lambda / GCP Cloud Functions (Serverless & Cost-Efficient)
If you want a 100% serverless deployment to save hosting costs:
* **Containerization**: Pack the Python environment, PyTorch, and transformers into a Docker container.
* **AWS ECR**: Push the container to AWS Elastic Container Registry.
* **AWS Lambda**: Deploy a Lambda function backed by the Docker image. Increase the function timeout to **15 minutes** and memory to **4GB**.

---

## ⏱️ 3. Scheduling Automated Runs (Cron Trigger)

The retail sentiment signals dictate entry strictly at the **market close of $T+1$**. Therefore, the pipeline must execute once daily, shortly before or after the stock market closes (e.g., 3:55 PM EST to enter on close, or 4:05 PM EST to submit orders for the next open).

### Using Linux Cron (EC2 Deployment)
Edit your crontab using `crontab -e` and add the following entry to trigger the pipeline every weekday at 3:55 PM EST (20:55 UTC):

```cron
55 20 * * 1-5 cd /app && /home/jules/.pyenv/shims/python wsb_alpha_system.py >> /var/log/wsb_pipeline.log 2>&1
```

### Using AWS EventBridge (Serverless Deployment)
1. Navigate to **Amazon EventBridge** -> **Rules** -> **Create Rule**.
2. Select **Schedule** as the rule type.
3. Enter a Cron expression: `cron(55 20 ? * MON-FRI *)` (runs at 20:55 UTC / 3:55 PM EST on weekdays).
4. Set the Target as your deployed **AWS Lambda** function.

---

## 🔒 4. Secure Secret Management

Never hardcode API keys, secret tokens, or passwords in your codebase!

1. **Environment Variables**: Read keys securely using `os.getenv()`.
2. **AWS Secrets Manager / Parameter Store**:
   - Store credentials securely on AWS.
   - Fetch them at runtime in your script using the AWS SDK (`boto3`):
     ```python
     import boto3
     import json

     def get_secret():
         client = boto3.client("secretsmanager", region_name="us-east-1")
         res = client.get_secret_value(SecretId="production/TradingKeys")
         return json.loads(res["SecretString"])
     ```

---

## 🚨 5. Logging, Monitoring, and Alerts

Automated trading requires bulletproof logging and real-time failure notifications.

1. **Email / SMS Alerts**: Use AWS SNS (Simple Notification Service) or Twilio to text you if an execution fails or broker orders are rejected.
2. **Discord / Slack Webhooks**: Send daily summaries or warning logs directly to your Discord/Slack channel:
   ```python
   import requests

   def notify_discord(message):
       webhook_url = "https://discord.com/api/webhooks/your-channel-id"
       requests.post(webhook_url, json={"content": message})
   ```
3. **Database Consistency**: The built-in `pricing_failed` blacklist in `wsb_factual_research_data.csv` ensures that failed tickers are permanently skipped, saving bandwidth, respecting yfinance rate limits, and avoiding trading errors.
