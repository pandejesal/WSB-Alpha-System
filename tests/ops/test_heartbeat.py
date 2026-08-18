import json
import os
import pytest
from datetime import datetime, timezone, timedelta

from src.ops.heartbeat import check_staleness, write_heartbeat, HEARTBEAT_FILE

@pytest.fixture(autouse=True)
def mock_heartbeat_file(tmp_path, monkeypatch):
    test_file = tmp_path / "heartbeat.json"
    monkeypatch.setattr("src.ops.heartbeat.HEARTBEAT_FILE", str(test_file))
    # Also patch write_artifact to use standard open for tests
    def mock_write(filename, data):
        with open(filename, 'w') as f:
            json.dump(data, f)
    monkeypatch.setattr("src.ops.heartbeat.write_artifact", mock_write)
    return str(test_file)

def test_heartbeat_staleness_missing_file():
    # File doesn't exist
    assert check_staleness() is True

def test_heartbeat_staleness_fresh(mock_heartbeat_file):
    write_heartbeat("test_run", "ok")
    assert check_staleness() is False

def test_heartbeat_staleness_stale(mock_heartbeat_file):
    # Manually write an old heartbeat and a slightly older one
    old_time = datetime.now(timezone.utc) - timedelta(hours=50)
    older_time = datetime.now(timezone.utc) - timedelta(hours=51)
    data = {
        "history": [
            {
                "job_name": "older_run",
                "ts": older_time.isoformat().replace("+00:00", "Z"),
                "status": "ok"
            },
            {
                "job_name": "old_run",
                "ts": old_time.isoformat().replace("+00:00", "Z"),
                "status": "ok"
            }
        ]
    }
    with open(mock_heartbeat_file, 'w') as f:
        json.dump(data, f)

    # Write a new heartbeat so we check the gap
    write_heartbeat("new_run", "ok")

    assert check_staleness() is True
