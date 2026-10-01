#!/usr/bin/env python3
"""
core/db_migrations/deactivate_shadow_names.py — Deactivates shadow name entries.
Sets in_anki = 0 for any is_name_entry = 1 entry that shares a reading with
an active real-word vocabulary entry (is_name_entry = 0 AND in_anki = 1).
Strictly <= 200 lines invariant.
"""

from __future__ import annotations

import os
import sqlite3
import time
from typing import Any, Dict, List, Set

DEFAULT_DICT_PATH = "/opt/japan/data/dict_index.sqlite3"


def get_db_path() -> str:
    candidates = [
        os.environ.get("DICT_INDEX_PATH", ""),
        DEFAULT_DICT_PATH,
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "dict_index.sqlite3"),
        "/opt/fleet/projects/japan/data/dict_index.sqlite3",
    ]
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return DEFAULT_DICT_PATH


def deactivate_shadow_names(db_path: str | None = None) -> Dict[str, Any]:
    path = db_path or get_db_path()
    if not os.path.isfile(path):
        return {"status": "error", "message": f"Database file not found: {path}"}

    conn = sqlite3.connect(path, timeout=30.0)
    cur = conn.cursor()

    try:
        t0 = time.time()
        # 1. Fetch all distinct readings of active real-word entries
        cur.execute(
            """
            SELECT DISTINCT r.reading 
            FROM reading_elements r 
            JOIN entries e ON e.id = r.entry_id 
            WHERE e.is_name_entry = 0 AND e.in_anki = 1
            """
        )
        real_readings: Set[str] = {row[0] for row in cur.fetchall() if row[0]}

        # 2. Find active name entries sharing readings with real words
        cur.execute(
            """
            SELECT DISTINCT e.id, r.reading 
            FROM reading_elements r 
            JOIN entries e ON e.id = r.entry_id 
            WHERE e.is_name_entry = 1 AND e.in_anki = 1
            """
        )
        name_rows = cur.fetchall()

        shadow_eids: Set[int] = set()
        shadow_samples: List[tuple[int, str]] = []
        for eid, reading in name_rows:
            if reading in real_readings:
                shadow_eids.add(eid)
                if len(shadow_samples) < 10:
                    shadow_samples.append((eid, reading))

        total_to_deactivate = len(shadow_eids)
        if total_to_deactivate == 0:
            return {
                "status": "noop",
                "message": "No shadow name entries found to deactivate.",
                "deactivated_count": 0,
            }

        # 3. Batch update in_anki = 0 in chunks
        eid_list = list(shadow_eids)
        chunk_size = 500
        for i in range(0, len(eid_list), chunk_size):
            chunk = eid_list[i : i + chunk_size]
            placeholders = ",".join("?" for _ in chunk)
            cur.execute(
                f"UPDATE entries SET in_anki = 0 WHERE id IN ({placeholders})",
                chunk,
            )

        conn.commit()
        elapsed = round(time.time() - t0, 3)

        # 4. Post-verification counts
        cur.execute("SELECT COUNT(*) FROM entries WHERE in_anki = 1 AND is_name_entry = 1")
        remaining_names = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM entries WHERE in_anki = 1 AND is_name_entry = 0")
        active_real_words = cur.fetchone()[0]

        return {
            "status": "ok",
            "deactivated_count": total_to_deactivate,
            "remaining_active_names": remaining_names,
            "active_real_words": active_real_words,
            "elapsed_seconds": elapsed,
            "sample_shadows": shadow_samples,
        }

    except Exception as exc:
        conn.rollback()
        return {"status": "error", "message": str(exc)}
    finally:
        conn.close()


if __name__ == "__main__":
    res = deactivate_shadow_names()
    print("Deactivation Result:", res)
