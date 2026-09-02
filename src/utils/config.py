import os

import yaml
from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class BenchmarkSpiderConfig(BaseModel):
    """SPY baseline benchmark configuration per paper 2608.26106 (score 10)."""
    enabled: bool = Field(default=True, description="Enable SPY baseline benchmark comparison")
    symbol: str = Field(default="SPY", description="Benchmark symbol for baseline comparison")
    lookback_days: int = Field(default=252, description="Trading days lookback for benchmark (1 year)")
    min_sharpe_ratio: float = Field(default=0.5, description="Minimum Sharpe ratio vs benchmark")
    max_drawdown_pct: float = Field(default=0.15, description="Maximum drawdown percentage vs benchmark")


class Settings(BaseSettings):
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")

    # Flat representation for proper loading
    alpaca_api_key: str = Field(default="", validation_alias="ALPACA_API_KEY")
    alpaca_secret_key: SecretStr = Field(default=SecretStr(""), validation_alias="ALPACA_SECRET_KEY")
    gemini_api_key: SecretStr = Field(default=SecretStr(""), validation_alias="GEMINI_API_KEY")
    anthropic_api_key: SecretStr = Field(default=SecretStr(""), validation_alias="ANTHROPIC_API_KEY")
    openrouter_api_key: SecretStr = Field(default=SecretStr(""), validation_alias="OPENROUTER_API_KEY")
    apify_token: SecretStr = Field(default=SecretStr(""), validation_alias="APIFY_TOKEN")
    reddit_client_id: str = Field(default="", validation_alias="REDDIT_CLIENT_ID")
    reddit_client_secret: SecretStr = Field(default=SecretStr(""), validation_alias="REDDIT_CLIENT_SECRET")
    binance_api_key: str = Field(default="", validation_alias="BINANCE_API_KEY")
    binance_secret_key: SecretStr = Field(default=SecretStr(""), validation_alias="BINANCE_SECRET_KEY")
    telegram_bot_token: SecretStr = Field(default=SecretStr(""), validation_alias="TELEGRAM_BOT_TOKEN")

    live_trading_enabled: bool = False
    paper_trading_enabled: bool = True
    initial_capital: float = 100.0

    benchmark_spider: BenchmarkSpiderConfig = Field(default_factory=BenchmarkSpiderConfig)

    @classmethod
    def load_from_yaml(cls, path="config/settings.yaml"):
        # Load default settings from yaml, then env variables override them automatically
        yaml_data = {}
        if os.path.exists(path):
            with open(path, "r") as f:
                data = yaml.safe_load(f) or {}
                if 'trading' in data:
                    yaml_data['live_trading_enabled'] = data['trading'].get('live_trading_enabled', False)
                    yaml_data['paper_trading_enabled'] = data['trading'].get('paper_trading_enabled', True)
                    yaml_data['initial_capital'] = data['trading'].get('initial_capital', 100.0)
                if 'benchmark_spider' in data:
                    yaml_data['benchmark_spider'] = data['benchmark_spider']
                yaml_data['environment'] = data.get('environment', 'development')

        return cls(**yaml_data)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

class APIKeysStub:
    def __init__(self, s):
        self.alpaca_api_key = s.alpaca_api_key
        self.alpaca_secret_key = s.alpaca_secret_key
        self.gemini_api_key = s.gemini_api_key
        self.anthropic_api_key = s.anthropic_api_key
        self.openrouter_api_key = s.openrouter_api_key
        self.apify_token = s.apify_token
        self.reddit_client_id = s.reddit_client_id
        self.reddit_client_secret = s.reddit_client_secret
        self.binance_api_key = s.binance_api_key
        self.binance_secret_key = s.binance_secret_key
        self.telegram_bot_token = s.telegram_bot_token

class TradingStub:
    def __init__(self, s):
        self.live_trading_enabled = s.live_trading_enabled
        self.paper_trading_enabled = s.paper_trading_enabled
        self.initial_capital = s.initial_capital

class BenchmarkSpiderStub:
    def __init__(self, s):
        bs = s.benchmark_spider
        self.enabled = bs.enabled
        self.symbol = bs.symbol
        self.lookback_days = bs.lookback_days
        self.min_sharpe_ratio = bs.min_sharpe_ratio
        self.max_drawdown_pct = bs.max_drawdown_pct

class ConfigWrapper:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.environment = settings.environment
        self.api_keys = APIKeysStub(settings)
        self.trading = TradingStub(settings)
        self.benchmark_spider = BenchmarkSpiderStub(settings)

config = ConfigWrapper(Settings.load_from_yaml())