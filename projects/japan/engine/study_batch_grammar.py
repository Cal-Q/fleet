#!/usr/bin/env python3
"""
engine/study_batch_grammar.py — Grammar Batch Staging & Sentence Ingestion
Stages example sentences, executes Anki synchronization, and audits card suspension.
Strictly <= 200 lines invariant.
"""

import json
import os
from typing import Any, Dict, List

from core.sync_worker import run_sync_and_push
from engine.sentence_gate import audit_and_suspend_sentences
from engine.study_queue import record_daily_batch, load_daily_stats

BASE_DIR = "/opt/japan"
DATA_DIR = os.path.join(BASE_DIR, "data")
JAPANESE_DIR = os.path.join(BASE_DIR, "japanese")
PENDING_SENTENCES_FILE = os.path.join(DATA_DIR, "bunpro_sentences_pending.json")
GRAMMAR_PROGRESS_FILE = os.path.join(JAPANESE_DIR, "grammar_progress.json")


def add_grammar_batch(grammar_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not grammar_list:
        return {"status": "ok", "message": "Nessun punto grammaticale fornito.", "today": load_daily_stats()}

    notes = []
    lesson_ids = []
    for g in grammar_list:
        lesson_ids.append(str(g["id"]))
        for s in g.get("sentences", [])[:5]:
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

    run_sync_and_push()
    audit_and_suspend_sentences()

    try:
        if os.path.exists(GRAMMAR_PROGRESS_FILE):
            with open(GRAMMAR_PROGRESS_FILE, "r", encoding="utf-8") as f:
                gp = json.load(f)
            for gid in lesson_ids:
                for _lvl, points in list(gp.get("unstudied_by_level", {}).items()):
                    for idx, pt in enumerate(points):
                        if str(pt.get("id")) == str(gid):
                            pt_found = points.pop(idx)
                            pt_found["studied"] = True
                            lvl_key = pt_found.get("level", "N3")
                            if "studied_by_level" not in gp:
                                gp["studied_by_level"] = {}
                            if lvl_key not in gp["studied_by_level"]:
                                gp["studied_by_level"][lvl_key] = []
                            gp["studied_by_level"][lvl_key].append(pt_found)
                            break
            with open(GRAMMAR_PROGRESS_FILE, "w", encoding="utf-8") as f:
                json.dump(gp, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    labels = [f"#{g.get('id')} {g.get('title', '')}" for g in grammar_list]
    stats = record_daily_batch("grammar", len(grammar_list), labels)
    return {"status": "ok", "message": f"Gruppo di {len(grammar_list)} Regole Grammaticali aggiunto!", "today": stats}
