#!/usr/bin/env python3
"""
core/anki_fatigue_snapshot_service.py — Persistence Service for Fatigue Prompt Snapshots
Stores exhaustive session card history and TPU neural features for every prompted pause.
Strictly <= 200 lines invariant.
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "dict_index.sqlite3")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_fatigue_prompt_table() -> None:
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fatigue_prompt_events (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                session_id TEXT,
                trigger_cid INTEGER,
                trigger_front TEXT,
                trigger_grade INTEGER,
                trigger_latency_ms INTEGER,
                drift REAL,
                lapse_risk REAL,
                mean_lat_10_ms REAL,
                mean_lat_30_ms REAL,
                recommended_sec INTEGER,
                reason TEXT,
                session_cards_count INTEGER,
                session_cards_json TEXT,
                neural_features_json TEXT,
                device TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_fatigue_prompts_created
            ON fatigue_prompt_events (created_at DESC)
        """)


def save_fatigue_prompt_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
    init_fatigue_prompt_table()
    now_iso = datetime.utcnow().isoformat() + "Z"
    event_id = event_data.get("id") or f"fp_{int(datetime.utcnow().timestamp()*1000)}"

    session_cards = event_data.get("session_cards", [])
    session_cards_json = json.dumps(session_cards, ensure_ascii=False) if isinstance(session_cards, list) else str(session_cards)

    neural_features = event_data.get("neural_features", [])
    neural_features_json = json.dumps(neural_features) if isinstance(neural_features, list) else str(neural_features)

    with get_db_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO fatigue_prompt_events (
                id, timestamp, session_id, trigger_cid, trigger_front,
                trigger_grade, trigger_latency_ms, drift, lapse_risk,
                mean_lat_10_ms, mean_lat_30_ms, recommended_sec,
                reason, session_cards_count, session_cards_json,
                neural_features_json, device, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            event_data.get("timestamp", now_iso),
            event_data.get("session_id", ""),
            event_data.get("trigger_cid"),
            event_data.get("trigger_front", ""),
            event_data.get("trigger_grade", 0),
            event_data.get("trigger_latency_ms", 0),
            float(event_data.get("drift", 0.0)),
            float(event_data.get("lapse_risk", 0.0)),
            float(event_data.get("mean_lat_10_ms", 0.0)),
            float(event_data.get("mean_lat_30_ms", 0.0)),
            int(event_data.get("recommended_sec", 60)),
            event_data.get("reason", ""),
            len(session_cards) if isinstance(session_cards, list) else int(event_data.get("session_cards_count", 0)),
            session_cards_json,
            neural_features_json,
            event_data.get("device", "unknown"),
            now_iso
        ))

    return {"status": "ok", "event_id": event_id, "cards_recorded": len(session_cards)}


def get_recent_fatigue_prompts(limit: int = 10) -> List[Dict[str, Any]]:
    init_fatigue_prompt_table()
    with get_db_connection() as conn:
        cursor = conn.execute("""
            SELECT * FROM fatigue_prompt_events
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()

    results = []
    for row in rows:
        d = dict(row)
        try:
            d["session_cards"] = json.loads(d.get("session_cards_json") or "[]")
        except Exception:
            d["session_cards"] = []
        try:
            d["neural_features"] = json.loads(d.get("neural_features_json") or "[]")
        except Exception:
            d["neural_features"] = []
        results.append(d)
    return results


def get_latest_fatigue_prompt() -> Optional[Dict[str, Any]]:
    recent = get_recent_fatigue_prompts(limit=1)
    return recent[0] if recent else None
