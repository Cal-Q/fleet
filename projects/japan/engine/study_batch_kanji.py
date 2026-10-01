#!/usr/bin/env python3
"""
engine/study_batch_kanji.py — Direct Kanji Note & Card Generation
Inserts KLC kanji cards directly into Anki collection and pushes to cloud.
Strictly <= 200 lines invariant.
"""

import time
from typing import Any, Dict, List

from core.db import open_dict_db
from core.sync_worker import run_sync_and_push
from engine.study_queue import record_daily_batch, load_daily_stats


def add_kanji_batch(kanji_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not kanji_list:
        return {
            "status": "ok",
            "message": "Nessun kanji fornito.",
            "today": load_daily_stats(),
        }

    chars = [k["kanji"] for k in kanji_list]
    now_ts = int(time.time())

    # 1. Update kanji_catalog directly in dict_index.sqlite3
    dict_conn = open_dict_db()
    cur = dict_conn.cursor()
    for k in chars:
        cur.execute(
            """
            UPDATE kanji_catalog
            SET in_anki = 1, status = 'studied', reps = 1, last_studied_at = ?
            WHERE kanji = ?
            """,
            (now_ts, k),
        )
    dict_conn.commit()
    dict_conn.close()

    # 2. Trigger pipeline to update Anki decks deterministically
    sync_ok, sync_msg = run_sync_and_push()

    labels = [
        f"#{k.get('id')} {k['kanji']} ({k.get('keyword', '')})"
        for k in kanji_list
    ]
    stats = record_daily_batch("kanji", len(kanji_list), labels)
    return {
        "status": "ok" if sync_ok else "warning",
        "message": (
            f"Gruppo di {len(kanji_list)} Kanji attivato in catalogo "
            "e sincronizzato!"
        ),
        "today": stats,
        "push_status": "success" if sync_ok else sync_msg,
        "added_count": len(kanji_list),
    }
