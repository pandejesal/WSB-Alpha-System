import json
import pytest
from unittest.mock import patch, MagicMock
from src.monitoring.telegram_bot import TelegramBot
from src.ops.heartbeat import HeartbeatManager
from src.ops.alerts import AlertManager
from datetime import datetime, timedelta, timezone
import os

@patch('requests.post')
def test_telegram_bot_send_alert(mock_post):
    mock_post.return_value.status_code = 200
    bot = TelegramBot()
    bot.bot_token = "test"
    bot.chat_id = "123"

    result = bot.send_alert("CRITICAL", "Test alert")
    assert result is True
    mock_post.assert_called_once()

    # Check payload
    call_args = mock_post.call_args[1]['json']
    assert "CRITICAL" in call_args['text']
    assert "🚨" in call_args['text']

@patch('requests.get')
def test_telegram_bot_poll_commands(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "ok": True,
        "result": [{"update_id": 1, "message": {"text": "/halt"}}]
    }
    mock_get.return_value = mock_response

    bot = TelegramBot()
    bot.bot_token = "test"
    updates = bot.poll_commands(offset=None)

    assert len(updates) == 1
    assert updates[0]["message"]["text"] == "/halt"

def test_heartbeat_staleness(tmp_path):
    filepath = str(tmp_path / "heartbeat.json")
    hm = HeartbeatManager(filepath=filepath)

    # No file -> not stale
    assert hm.check_staleness() is False

    # Write a fresh heartbeat
    hm.write_heartbeat("run_123")
    assert hm.check_staleness() is False

    # Write a stale heartbeat (3 days old)
    with open(filepath, "w") as f:
        stale_ts = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat().replace("+00:00", "Z")
        json.dump({"run_id": "stale", "ts": stale_ts}, f)

    assert hm.check_staleness() is True

@patch('src.monitoring.telegram_bot.TelegramBot.send_message')
def test_alert_manager_digest(mock_send, tmp_path):
    mock_send.return_value = True

    am = AlertManager()

    with patch('os.path.exists', return_value=False):
        am.compile_daily_digest()

    mock_send.assert_called_once()
    assert "Daily Ops Digest" in mock_send.call_args[0][0]

@patch('src.monitoring.telegram_bot.TelegramBot.send_message')
def test_alert_manager_fallback(mock_send, tmp_path):
    mock_send.return_value = False

    am = AlertManager()

    with patch('src.ops.alerts.AlertManager._write_fallback_alert') as mock_fallback, \
         patch('os.path.exists', return_value=False):
        am.compile_daily_digest()

    mock_send.assert_called_once()
    mock_fallback.assert_called_once()
