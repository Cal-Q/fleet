"""Merges vocab queued into the SQLite dict_index database without JSON files."""

from __future__ import annotations

import sqlite3
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .anki_deck_manager import AnkiDeckManager

DICT_INDEX_PATH = "/opt/japan/data/dict_index.sqlite3"


def ensure_queue_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bunpro_vocab_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            english TEXT NOT NULL,
            kana TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at INTEGER DEFAULT 0,
            synced_at INTEGER DEFAULT 0
        )
        """
    )


def apply_pending_vocab(
    collection_path: str = "",
    deck_manager: AnkiDeckManager | None = None,
    db_path: str = DICT_INDEX_PATH,
) -> int:
    conn = sqlite3.connect(db_path)
    try:
        ensure_queue_table(conn)
        cur = conn.cursor()
        cur.execute("SELECT id, english, kana FROM bunpro_vocab_queue WHERE status = 'pending' ORDER BY id ASC")
        pending_rows = cur.fetchall()

        if not pending_rows:
            return 0

        cur.execute(
            """
            SELECT DISTINCT r.reading 
            FROM reading_elements r 
            JOIN entries e ON e.id = r.entry_id 
            WHERE e.in_anki = 1
            """
        )
        existing_kana = {row[0] for row in cur.fetchall()}

        now = int(time.time())
        changed = 0
        synced_ids = []

        for qid, english, kana in pending_rows:
            # Find matching entries in JMdict
            cur.execute(
                """
                SELECT e.id 
                FROM entries e 
                JOIN reading_elements r ON r.entry_id = e.id 
                WHERE r.reading = ? AND e.in_anki = 0
                """,
                (kana,),
            )
            matching_ids = [r[0] for r in cur.fetchall()]
            if matching_ids:
                ph = ",".join("?" for _ in matching_ids)
                cur.execute(f"UPDATE entries SET in_anki = 1 WHERE id IN ({ph})", matching_ids)
                changed += len(matching_ids)
            synced_ids.append(qid)

        if synced_ids:
            ph = ",".join("?" for _ in synced_ids)
            cur.execute(f"UPDATE bunpro_vocab_queue SET status = 'synced', synced_at = ? WHERE id IN ({ph})", [now] + synced_ids)

        if changed:
            conn.commit()
        return changed
    finally:
        conn.close()
