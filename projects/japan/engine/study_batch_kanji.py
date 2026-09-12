#!/usr/bin/env python3
"""
engine/study_batch_kanji.py — Direct Kanji Note & Card Generation
Inserts KLC kanji cards directly into Anki collection and pushes to cloud.
Strictly <= 200 lines invariant.
"""

import json
import os
import sys
import time
from typing import Any, Dict, List

from core.db import open_dict_db, get_anki_db_path
from core.sync_worker import run_sync_and_push
from engine.study_queue import record_daily_batch, load_daily_stats

BASE_DIR = "/opt/japan"
JAPANESE_DIR = os.path.join(BASE_DIR, "japanese")
USER_KANJI_CACHE = os.path.join(JAPANESE_DIR, "user_studied_kanji.json")


def add_kanji_batch(kanji_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not kanji_list:
        return {"status": "ok", "message": "Nessun kanji fornito.", "today": load_daily_stats()}

    chars = [k["kanji"] for k in kanji_list]
    placeholders = ",".join("?" * len(chars))

    dict_conn = open_dict_db()
    cur = dict_conn.cursor()
    cur.execute(f"SELECT kanji, number, image FROM source_kanji_images WHERE kanji IN ({placeholders})", chars)
    kanji_data = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
    dict_conn.close()

    if "/usr/local/share/anki/app_packages" not in sys.path:
        sys.path.insert(0, "/usr/local/share/anki/app_packages")
    from anki.collection import Collection

    col = Collection(get_anki_db_path())
    deck = col.decks.by_name("[JAP]::[TRAVEL]::Kanji - Image Deck") or col.decks.by_name("[JAP]::[TRAVEL]::[SOURCE] Kanji - Image Deck")
    did = deck["id"]
    model = col.models.by_name("Kanji Image Model")

    now_ts = int(time.time())
    for k in chars:
        num, img = kanji_data.get(k, (0, f'<hr><img src="{k}.png">'))
        note = col.new_note(model)
        note["Kanji"] = k
        note["Image"] = img
        note["Number"] = str(num)
        col.add_note(note, did)

        for c in note.cards():
            col.db.execute("""
                UPDATE cards 
                SET reps = 1, type = 1, queue = 1, mod = ?, usn = -1 
                WHERE id = ?
            """, (now_ts, c.id))
            col.db.execute("""
                INSERT INTO revlog (id, cid, usn, ease, ivl, lastIvl, factor, time, type)
                VALUES (?, ?, -1, 3, 1, 0, 2500, 5000, 0)
            """, (int(time.time() * 1000) + (c.id % 1000), c.id))

    col.save()
    col.close()

    run_sync_and_push()

    try:
        if os.path.exists(USER_KANJI_CACHE):
            with open(USER_KANJI_CACHE, "r", encoding="utf-8") as f:
                c_set = set(json.load(f))
            c_set.update(chars)
            with open(USER_KANJI_CACHE, "w", encoding="utf-8") as f:
                json.dump(sorted(list(c_set)), f, ensure_ascii=False)
    except Exception:
        pass

    labels = [f"#{k.get('id')} {k['kanji']} ({k.get('keyword', '')})" for k in kanji_list]
    stats = record_daily_batch("kanji", len(kanji_list), labels)
    return {"status": "ok", "message": f"Gruppo di {len(kanji_list)} Kanji aggiunto e sincronizzato!", "today": stats}
