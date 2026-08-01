import os
from pydantic import BaseModel, Field, SecretStr
from dotenv import load_dotenv

load_dotenv()

class APIKeys(BaseModel):
    alpaca_api_key: str = Field(default_factory=lambda: os.getenv("ALPACA_API_KEY", ""))
    alpaca_secret_key: SecretStr = Field(default_factory=lambda: SecretStr(os.getenv("ALPACA_SECRET_KEY", "")))
    gemini_api_key: SecretStr = Field(default_factory=lambda: SecretStr(os.getenv("GEMINI_API_KEY", "")))
    anthropic_api_key: SecretStr = Field(default_factory=lambda: SecretStr(os.getenv("ANTHROPIC_API_KEY", "")))
    openrouter_api_key: SecretStr = Field(default_factory=lambda: SecretStr(os.getenv("OPENROUTER_API_KEY", "")))
    apify_token: SecretStr = Field(default_factory=lambda: SecretStr(os.getenv("APIFY_TOKEN", "")))
    reddit_client_id: str = Field(default_factory=lambda: os.getenv("REDDIT_CLIENT_ID", ""))
    reddit_client_secret: SecretStr = Field(default_factory=lambda: SecretStr(os.getenv("REDDIT_CLIENT_SECRET", "")))
    binance_api_key: str = Field(default_factory=lambda: os.getenv("BINANCE_API_KEY", ""))
    binance_secret_key: SecretStr = Field(default_factory=lambda: SecretStr(os.getenv("BINANCE_SECRET_KEY", "")))
    telegram_bot_token: SecretStr = Field(default_factory=lambda: SecretStr(os.getenv("TELEGRAM_BOT_TOKEN", "")))

class TradingConfig(BaseModel):
    live_trading_enabled: bool = False
    paper_trading_enabled: bool = True
    initial_capital: float = 100.0

class AppConfig(BaseModel):
    api_keys: APIKeys = Field(default_factory=APIKeys)
    trading: TradingConfig = Field(default_factory=TradingConfig)

config = AppConfig()
