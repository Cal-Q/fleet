#!/usr/bin/env python3
"""
engine/study_batch_vocab.py — Vocabulary Batch Staging & Resolution
Resolves JMdict definitions, stages into bunpro_vocab_pending.json, and pushes to cloud.
Strictly <= 200 lines invariant.
"""

import json
import os
from typing import Any, Dict, List

from core.db import open_dict_db
from core.sync_worker import run_sync_and_push
from engine.study_queue import record_daily_batch, load_daily_stats

BASE_DIR = "/opt/japan"
DATA_DIR = os.path.join(BASE_DIR, "data")
PENDING_VOCAB_FILE = os.path.join(DATA_DIR, "bunpro_vocab_pending.json")


def add_vocab_batch(vocab_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not vocab_list:
        return {"status": "ok", "message": "Nessun vocabolo fornito.", "today": load_daily_stats()}

    dict_conn = open_dict_db()
    cur = dict_conn.cursor()

    cur.execute("SELECT english, kana FROM source_english_to_kana")
    existing = {r[0]: r[1] for r in cur.fetchall()}

    pending = {}
    if os.path.exists(PENDING_VOCAB_FILE):
        try:
            with open(PENDING_VOCAB_FILE, "r", encoding="utf-8") as f:
                pending = json.load(f)
        except Exception:
            pending = {}

    for v in vocab_list:
        word = v.get("word", "")
        reading = v.get("reading", "")
        meaning = v.get("meaning", "")

        cur.execute("""
            SELECT e.id, g.text 
            FROM reading_elements re
            JOIN entries e ON re.entry_id = e.id
            JOIN senses s ON s.entry_id = e.id
            JOIN glosses g ON g.sense_id = s.id
            WHERE re.reading IN (?, ?) AND e.is_name_entry = 0
            ORDER BY (re.reading = ?) DESC, s.ord ASC, g.ord ASC
        """, (word, reading, word))
        rows = cur.fetchall()
        gloss = meaning
        if rows:
            m_low = meaning.lower()
            for _eid, g_text in rows:
                if g_text.lower().strip() in m_low or m_low in g_text.lower().strip():
                    gloss = g_text
                    break
            else:
                gloss = rows[0][1]

        pending[gloss] = reading
        if gloss not in existing:
            cur.execute("INSERT INTO source_english_to_kana (english, kana) VALUES (?, ?)", (gloss, reading))
            existing[gloss] = reading
        elif existing[gloss] != reading:
            cur.execute("UPDATE source_english_to_kana SET kana = ? WHERE english = ?", (reading, gloss))

    dict_conn.commit()
    dict_conn.close()

    tmp = PENDING_VOCAB_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)
    os.replace(tmp, PENDING_VOCAB_FILE)

    run_sync_and_push()

    labels = [f"{v.get('word', '')} ({v.get('reading', '')})" for v in vocab_list]
    stats = record_daily_batch("vocab", len(vocab_list), labels)
    return {"status": "ok", "message": f"Gruppo di {len(vocab_list)} Vocaboli aggiunto e sincronizzato!", "today": stats}
