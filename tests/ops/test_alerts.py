import pytest
from unittest.mock import patch, MagicMock

from src.ops.alerts import Alerts

@patch('src.monitoring.telegram_bot.requests.post')
def test_alerts_severity_ladder(mock_post, monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    monkeypatch.setattr("src.monitoring.telegram_bot.config.api_keys.telegram_bot_token", "dummy")

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_post.return_value = mock_resp

    alerts = Alerts()

    alerts.send_info("test info")
    mock_post.assert_called_with("https://api.telegram.org/botdummy/sendMessage",
                                json={"chat_id": "123", "text": "ℹ️ [INFO] test info", "parse_mode": "HTML"},
                                timeout=10)

    alerts.send_warn("test warn")
    mock_post.assert_called_with("https://api.telegram.org/botdummy/sendMessage",
                                json={"chat_id": "123", "text": "⚠️ [WARN] test warn", "parse_mode": "HTML"},
                                timeout=10)

    alerts.send_critical("test crit")
    mock_post.assert_called_with("https://api.telegram.org/botdummy/sendMessage",
                                json={"chat_id": "123", "text": "🚨 [CRITICAL] test crit", "parse_mode": "HTML"},
                                timeout=10)

@patch('src.monitoring.telegram_bot.requests.post')
def test_alerts_daily_digest(mock_post, monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    monkeypatch.setattr("src.monitoring.telegram_bot.config.api_keys.telegram_bot_token", "dummy")

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_post.return_value = mock_resp

    alerts = Alerts()
    alerts.send_daily_digest({"trades": 5, "equity": 150.0, "pnl_pct": 0.05})

    assert mock_post.called
    call_args = mock_post.call_args[1]['json']['text']
    assert "Daily Trade Summary" in call_args
    assert "5" in call_args
    assert "$150.00" in call_args
    assert "5.00%" in call_args
