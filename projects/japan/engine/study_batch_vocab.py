#!/usr/bin/env python3
"""
engine/study_batch_vocab.py — Vocabulary Batch Staging & Resolution
Resolves JMdict definitions, stages into bunpro_vocab_pending.json, and pushes to cloud.
Strictly <= 200 lines invariant.
"""

import json
import os
import time
from typing import Any, Dict, List

from core.db import open_dict_db, clean_kana
from core.sync_worker import run_sync_and_push
from engine.study_queue import record_daily_batch, load_daily_stats
from engine.vocab_meanings_resolver import resolve_multi_meanings

BASE_DIR = "/opt/japan"
DATA_DIR = os.path.join(BASE_DIR, "data")
PENDING_VOCAB_FILE = os.path.join(DATA_DIR, "bunpro_vocab_pending.json")


def get_vocab_deck_stats() -> Dict[str, Any]:
    try:
        from core.db import open_anki_db
        col = open_anki_db()
        cur = col.cursor()
        cur.execute(
            """
            SELECT sum(case when reps=0 then 1 else 0 end),
                   sum(case when reps>0 then 1 else 0 end),
                   count(*)
            FROM cards WHERE did=1759999324396
            """
        )
        r = cur.fetchone()
        col.close()
        return {"new": r[0] or 0, "mature": r[1] or 0, "total": r[2] or 0}
    except Exception:
        return {}


def add_vocab_batch(vocab_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not vocab_list:
        return {
            "status": "ok",
            "message": "Nessun vocabolo fornito.",
            "today": load_daily_stats(),
        }

    dict_conn = open_dict_db()
    cur = dict_conn.cursor()
    cur.execute(
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
    cur.execute("SELECT english, kana FROM bunpro_vocab_queue")
    existing = {r[0]: r[1] for r in cur.fetchall()}

    pending = {}
    if os.path.exists(PENDING_VOCAB_FILE):
        try:
            with open(PENDING_VOCAB_FILE, "r", encoding="utf-8") as f:
                pending = json.load(f)
        except Exception:
            pending = {}

    added_words_details: List[Dict[str, Any]] = []
    now_ts = int(time.time())
    for v in vocab_list:
        word = v.get("word", "")
        raw_reading = v.get("reading", "")
        reading = clean_kana(raw_reading, word)
        input_meaning = v.get("meaning", "")

        meanings = resolve_multi_meanings(cur, word, reading, input_meaning, limit=3)
        cur.execute(
            """
            UPDATE entries SET in_anki = 1
            WHERE id IN (
                SELECT entry_id FROM reading_elements WHERE reading IN (?, ?)
            )
            """,
            (word, reading),
        )
        cur.execute(
            """
            UPDATE jlpt_vocab
            SET in_anki = 1, status = 'studied'
            WHERE word = ? OR reading = ?
            """,
            (word, reading),
        )
        for m in meanings:
            gloss = m
            if gloss in existing and existing[gloss] != reading:
                gloss = f"{gloss} [{word}]"

            pending[gloss] = reading
            if gloss not in existing:
                cur.execute(
                    """
                    INSERT INTO bunpro_vocab_queue (english, kana, status, created_at)
                    VALUES (?, ?, 'pending', ?)
                    """,
                    (gloss, reading, now_ts),
                )
                existing[gloss] = reading

        bulleted_meanings = "<br>".join(f"- {m}" for m in meanings)
        added_words_details.append({
            "word": word,
            "details": f"{raw_reading or reading}<br>{bulleted_meanings}",
            "ruby": raw_reading or reading,
            "meanings": meanings,
        })

    dict_conn.commit()
    dict_conn.close()

    tmp = PENDING_VOCAB_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)
    os.replace(tmp, PENDING_VOCAB_FILE)

    sync_ok, sync_msg = run_sync_and_push()

    anki_stats = get_vocab_deck_stats()
    labels = [f"{v.get('word', '')} ({v.get('reading', '')})" for v in vocab_list]
    stats = record_daily_batch("vocab", len(vocab_list), labels)
    return {
        "status": "ok" if sync_ok else "warning",
        "message": f"Gruppo di {len(vocab_list)} Vocaboli aggiunto e sincronizzato!",
        "today": stats,
        "anki_stats": anki_stats,
        "push_status": "success" if sync_ok else sync_msg,
        "added_count": len(vocab_list),
    }
