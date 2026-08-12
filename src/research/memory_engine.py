import json
import logging
import sqlite3
from typing import Any

logger = logging.getLogger(__name__)

class MemoryEngine:
    def __init__(self, db_path: str = "memory_engine.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Table for blocked combinations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blocked_combos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    combo_json TEXT UNIQUE,
                    reason TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Table for performance outcomes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    combo_json TEXT UNIQUE,
                    performance_json TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def _normalize_combo(self, combo: dict[str, Any]) -> str:
        # Sort keys to ensure the JSON string is consistent for the same dictionary
        return json.dumps(combo, sort_keys=True)

    def block_combo(self, combo: dict[str, Any], reason: str):
        combo_str = self._normalize_combo(combo)
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO blocked_combos (combo_json, reason)
                    VALUES (?, ?)
                """, (combo_str, reason))
                conn.commit()
                logger.info(f"Blocked combo: {combo_str} Reason: {reason}")
        except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
            logger.error(f"Error blocking combo: {e}")

    def record_outcome(self, combo: dict[str, Any], performance: dict[str, Any]):
        combo_str = self._normalize_combo(combo)
        perf_str = json.dumps(performance)
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO performance_outcomes (combo_json, performance_json)
                    VALUES (?, ?)
                """, (combo_str, perf_str))
                conn.commit()
                logger.info(f"Recorded outcome for: {combo_str}")
        except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
            logger.error(f"Error recording outcome: {e}")

    def is_blocked(self, combo: dict[str, Any]) -> bool:
        combo_str = self._normalize_combo(combo)
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM blocked_combos WHERE combo_json = ?", (combo_str,))
                return cursor.fetchone() is not None
        except Exception as e:  # noqa: BLE001 - Catching Exception to fail gracefully
            logger.error(f"Error checking if blocked: {e}")
            return False

    def recommend_params(self, candidate_combos: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Given a list of candidate combinations, returns only those that are NOT blocked.
        """
        recommended = []
        for combo in candidate_combos:
            if not self.is_blocked(combo):
                recommended.append(combo)
        return recommended
