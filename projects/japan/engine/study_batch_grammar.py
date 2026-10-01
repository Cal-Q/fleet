#!/usr/bin/env python3
"""
engine/study_batch_grammar.py — Grammar Batch Staging & Sentence Ingestion
Stages example sentences, executes Anki synchronization, and audits card suspension.
Strictly <= 200 lines invariant.
"""

import json
import os
import time
from typing import Any, Dict, List

from collections import defaultdict
from core.db import open_dict_db, clean_kana
from core.sync_worker import run_sync_and_push
from engine.grammar_vocab_gate import get_reviewed_vocab_set
from engine.study_queue import record_daily_batch, load_daily_stats

BASE_DIR = "/opt/japan"
DATA_DIR = os.path.join(BASE_DIR, "data")
PENDING_SENTENCES_FILE = os.path.join(DATA_DIR, "bunpro_sentences_pending.json")


def add_grammar_batch(grammar_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not grammar_list:
        return {
            "status": "ok",
            "message": "Nessun punto grammaticale fornito.",
            "today": load_daily_stats(),
        }

    # Strict Invariant: Check prerequisite Bunpro vocabulary coverage
    reviewed = get_reviewed_vocab_set()
    conn = open_dict_db()
    conn.row_factory = None
    cur = conn.cursor()
    try:
        gids = [g.get("id") for g in grammar_list if g.get("id")]
        cov = defaultdict(list)
        if gids:
            ph = ",".join("?" * len(gids))
            q = (
                "SELECT grammar_id, title, furigana FROM "
                f"bunpro_grammar_vocab_coverage WHERE grammar_id IN ({ph})"
            )
            cur.execute(q, gids)
            for gid, title, furi in cur.fetchall():
                cov[gid].append((title, furi))
    finally:
        conn.close()

    blocked = []
    for g in grammar_list:
        gid = g.get("id")
        missing = [
            w for w, furi in cov.get(gid, [])
            if w not in reviewed and clean_kana(furi, w) not in reviewed
        ]
        if missing:
            blocked.append(
                f"#{gid} {g.get('title', '')} (mancano: {', '.join(missing[:3])})"
            )

    if blocked:
        return {
            "status": "error",
            "message": (
                "Aggiunta bloccata: vocaboli REQ non ancora studiati per: "
                f"{', '.join(blocked)}"
            ),
        }

    notes = []
    lesson_ids = []
    for g in grammar_list:
        lesson_ids.append(str(g["id"]))
        target_sents = [
            s for s in g.get("sentences", [])
            if s.get("question_type") == "cloze"
        ] or g.get("sentences", [])
        for s in target_sents[:5]:
            notes.append({
                "deckName": "[JAP]::[TRAVEL]::[1] Jap Sentences",
                "modelName": "Jap Sentences",
                "mainField": "Japanese",
                "fields": {
                    "English": s.get("clean_en", ""),
                    "Japanese": s.get("clean_jp") or s.get("plain_jp", ""),
                    "Audio": ""
                },
                "audio": []
            })

    existing = []
    if os.path.exists(PENDING_SENTENCES_FILE):
        try:
            with open(PENDING_SENTENCES_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []

    existing.extend(notes)
    tmp = PENDING_SENTENCES_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    os.replace(tmp, PENDING_SENTENCES_FILE)

    conn = open_dict_db()
    cur = conn.cursor()
    now_ts = int(time.time() * 1000)
    for gid in lesson_ids:
        cur.execute(
            """
            UPDATE bunpro_grammar_points
            SET in_anki = 1, status = 'studied', studied_at = ?
            WHERE id = ?
            """,
            (now_ts, int(gid)),
        )
    conn.commit()
    conn.close()

    anki_stats = {}
    sync_ok, sync_msg = run_sync_and_push()
    try:
        from core.db import open_anki_db
        c_db = open_anki_db()
        cur_g = c_db.cursor()
        cur_g.execute(
            """
            SELECT sum(case when reps=0 then 1 else 0 end),
                   sum(case when reps>0 then 1 else 0 end),
                   count(*)
            FROM cards WHERE did=1770845308673
            """
        )
        r_g = cur_g.fetchone()
        c_db.close()
        anki_stats = {
            "new": r_g[0] or 0,
            "mature": r_g[1] or 0,
            "total": r_g[2] or 0,
        }
    except Exception:
        pass

    labels = [f"#{g.get('id')} {g.get('title', '')}" for g in grammar_list]
    stats = record_daily_batch("grammar", len(grammar_list), labels)
    return {
        "status": "ok" if sync_ok else "warning",
        "message": f"Gruppo di {len(grammar_list)} Regole Grammaticali aggiunto!",
        "today": stats,
        "anki_stats": anki_stats,
        "push_status": "success" if sync_ok else sync_msg,
        "added_count": len(grammar_list)
    }

