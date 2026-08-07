import pytest
import tempfile
import json
import sqlite3
import os

from src.research.memory_engine import MemoryEngine

@pytest.fixture
def memory_engine():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test_memory.db")
        engine = MemoryEngine(db_path=db_path)
        yield engine

def test_memory_engine_init(memory_engine):
    assert os.path.exists(memory_engine.db_path)

    with sqlite3.connect(memory_engine.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        assert "blocked_combos" in tables
        assert "performance_outcomes" in tables

def test_block_combo(memory_engine):
    combo = {"rsi_bounds": [30, 70], "atr_mult": 2.0}
    reason = "Poor WF efficiency"

    assert not memory_engine.is_blocked(combo)

    memory_engine.block_combo(combo, reason)
    assert memory_engine.is_blocked(combo)

    # Should replace if blocked again
    memory_engine.block_combo(combo, "Even worse reason")

    with sqlite3.connect(memory_engine.db_path) as conn:
        cursor = conn.cursor()
        combo_str = memory_engine._normalize_combo(combo)
        cursor.execute("SELECT reason FROM blocked_combos WHERE combo_json = ?", (combo_str,))
        row = cursor.fetchone()
        assert row[0] == "Even worse reason"

def test_record_outcome(memory_engine):
    combo = {"rsi_bounds": [35, 65], "atr_mult": 1.5}
    perf = {"avg_wf_efficiency": 0.85, "sharpe": 1.2}

    memory_engine.record_outcome(combo, perf)

    with sqlite3.connect(memory_engine.db_path) as conn:
        cursor = conn.cursor()
        combo_str = memory_engine._normalize_combo(combo)
        cursor.execute("SELECT performance_json FROM performance_outcomes WHERE combo_json = ?", (combo_str,))
        row = cursor.fetchone()
        saved_perf = json.loads(row[0])
        assert saved_perf["avg_wf_efficiency"] == 0.85
        assert saved_perf["sharpe"] == 1.2

def test_recommend_params(memory_engine):
    combo1 = {"param": "A"}
    combo2 = {"param": "B"}
    combo3 = {"param": "C"}

    memory_engine.block_combo(combo2, "Bad performance")

    candidates = [combo1, combo2, combo3]
    recommended = memory_engine.recommend_params(candidates)

    assert len(recommended) == 2
    assert combo1 in recommended
    assert combo3 in recommended
    assert combo2 not in recommended
