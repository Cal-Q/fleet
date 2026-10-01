#!/usr/bin/env python3
"""
core/cooldown_scheduler.py — Spreads new cards across N days with cooldown.
Applies review scheduling (type=2, queue=2, factor=2500) with staggered due dates.
Strictly <= 200 lines invariant.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import time
from typing import Any, Dict, List

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from core.anki_sm2 import get_today_days
from core.anki_sync.backup_sentinel import create_snapshot
from core.db import get_anki_db_path, open_anki_db

TARGET_DECK_NAME = "[JAP]\x1f[TRAVEL]\x1fJapanese -> Phonetic + Meaning"


def spread_new_vocab_cards(
    days: int = 30,
    target_did: int | None = None
) -> Dict[str, Any]:
    col_path = get_anki_db_path()
    if not os.path.isfile(col_path):
        return {"status": "error", "message": f"Collection not found at {col_path}"}

    # 1. Create atomic backup snapshot
    snapshot_file = create_snapshot(col_path)

    conn = open_anki_db(timeout=30.0)
    cur = conn.cursor()

    try:
        # Find deck ID if not passed
        if not target_did:
            cur.execute("SELECT id FROM decks WHERE name = ?", (TARGET_DECK_NAME,))
            row = cur.fetchone()
            if not row:
                return {"status": "error", "message": f"Deck '{TARGET_DECK_NAME}' not found"}
            target_did = row[0]

        today_days = get_today_days(cur)
        now_ts = int(time.time())
        now_ms = int(time.time() * 1000)

        # 2. Select all new cards for target deck
        cur.execute(
            "SELECT id, due FROM cards WHERE did = ? AND queue = 0 ORDER BY due ASC, id ASC",
            (target_did,)
        )
        new_cards = cur.fetchall()
        total_count = len(new_cards)

        if total_count == 0:
            return {
                "status": "noop",
                "message": "No new cards found in target deck",
                "total_updated": 0
            }

        # 3. Calculate staggered schedule
        # Distribute evenly across 1..days
        updates: List[tuple[int, int, int, int, int, int, int, int, int, int]] = []
        day_counts: Dict[int, int] = {d: 0 for d in range(1, days + 1)}

        for idx, (cid, _) in enumerate(new_cards):
            day_offset = 1 + (idx * days) // total_count
            day_counts[day_offset] += 1
            new_due = today_days + day_offset
            new_ivl = day_offset

            # params: (mod, usn, type, queue, due, ivl, factor, reps, lapses, id)
            updates.append((now_ts, -1, 2, 2, new_due, new_ivl, 2500, 0, 0, cid))

        # 4. Apply batch update
        cur.executemany(
            """
            UPDATE cards 
            SET mod = ?, usn = ?, type = ?, queue = ?, due = ?, ivl = ?, factor = ?, reps = ?, lapses = ?
            WHERE id = ?
            """,
            updates
        )

        # 5. Update collection metadata
        cur.execute("UPDATE col SET mod = ?, usn = -1", (now_ms,))
        conn.commit()

        return {
            "status": "ok",
            "deck_id": target_did,
            "total_updated": total_count,
            "days_spread": days,
            "today_days": today_days,
            "due_range": (today_days + 1, today_days + days),
            "distribution_summary": {
                "min_per_day": min(day_counts.values()),
                "max_per_day": max(day_counts.values()),
                "sample_days": {k: day_counts[k] for k in list(day_counts.keys())[:5]}
            },
            "snapshot_backup": snapshot_file
        }

    except Exception as exc:
        conn.rollback()
        return {"status": "error", "message": str(exc)}
    finally:
        conn.close()


if __name__ == "__main__":
    result = spread_new_vocab_cards(days=30)
    print("Result:", result)
