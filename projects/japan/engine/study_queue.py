#!/usr/bin/env python3
"""
engine/study_queue.py — Curriculum Queue Provider for Kanji, Vocab, and Grammar
Fetches unstudied batches sorted by N-level ascending, then canonical ID.
Strictly <= 200 lines invariant.
"""

from datetime import datetime
import json
import os
import sys
from typing import Any, Dict, List, Set

from core.db import open_anki_db
from engine.grammar_vocab_gate import (
    get_grammar_priority_vocab,
    evaluate_grammar_queue,
    load_cached_json,
    LEVEL_ORDER
)

BASE_DIR = "/opt/japan"
JAPANESE_DIR = os.path.join(BASE_DIR, "japanese")
KODANSHA_FILE = os.path.join(JAPANESE_DIR, "kodansha_kanji.json")
STUDIED_KANJI_FILE = os.path.join(JAPANESE_DIR, "user_studied_kanji.json")
DAILY_LOG_FILE = os.path.join(JAPANESE_DIR, "daily_additions.json")

_KODANSHA_CACHE: List[Dict[str, Any]] = []
_KODANSHA_MTIME: float = 0.0


def get_today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def load_daily_stats() -> Dict[str, Any]:
    today = get_today_str()
    data = load_cached_json(DAILY_LOG_FILE)
    if isinstance(data, dict) and today in data:
        return data[today]
    return {"date": today, "kanji": 0, "vocab": 0, "grammar": 0, "items": []}


def record_daily_batch(category: str, count: int, labels: List[str]) -> Dict[str, Any]:
    today = get_today_str()
    data = {}
    if os.path.exists(DAILY_LOG_FILE):
        try:
            with open(DAILY_LOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}

    if today not in data:
        data[today] = {"date": today, "kanji": 0, "vocab": 0, "grammar": 0, "items": []}

    data[today][category] = data[today].get(category, 0) + count
    for lbl in labels:
        data[today]["items"].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "category": category,
            "label": lbl
        })

    with open(DAILY_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data[today]


def get_studied_kanji_set(refresh: bool = False) -> Set[str]:
    if not refresh and os.path.exists(STUDIED_KANJI_FILE):
        cached = load_cached_json(STUDIED_KANJI_FILE)
        if isinstance(cached, list):
            return set(cached)

    try:
        col = open_anki_db()
        cur = col.cursor()
        cur.execute("SELECT notes.flds FROM notes JOIN cards ON notes.id=cards.nid WHERE cards.did=1757158925901 AND cards.reps>0")
        res = {r[0].split(chr(31))[0].strip()[0] for r in cur.fetchall() if r[0]}
        col.close()

        with open(STUDIED_KANJI_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(res)), f, ensure_ascii=False)
        return res
    except Exception as e:
        print(f"Error querying studied kanji from local Anki: {e}", file=sys.stderr)
        return set()


def get_next_items(
    kanji_limit: int = 5,
    vocab_limit: int = 20,
    grammar_limit: int = 5
) -> Dict[str, Any]:
    today_stats = load_daily_stats()

    # 1. KANJI
    studied_kanji = get_studied_kanji_set()
    global _KODANSHA_CACHE, _KODANSHA_MTIME
    kanji_items = []
    if os.path.exists(KODANSHA_FILE):
        mtime = os.path.getmtime(KODANSHA_FILE)
        if not _KODANSHA_CACHE or mtime != _KODANSHA_MTIME:
            with open(KODANSHA_FILE, "r", encoding="utf-8") as f:
                _KODANSHA_CACHE = json.load(f)
            _KODANSHA_MTIME = mtime
        unstudied_k = [k for k in _KODANSHA_CACHE if k["kanji"] not in studied_kanji]
        unstudied_k.sort(key=lambda k: (LEVEL_ORDER.get(k.get("jlpt_level", "Hyōgai"), 99), k["id"]))
        kanji_items = unstudied_k[:kanji_limit]

    # 2. VOCAB (Prioritizes unstudied vocab required by upcoming grammar rules)
    vocab_items = get_grammar_priority_vocab(vocab_limit=vocab_limit)

    # 3. GRAMMAR (Gated: only rules whose valid dictionary vocabularies have reps >= 1)
    unlocked_g, locked_g = evaluate_grammar_queue(grammar_limit=grammar_limit)

    return {
        "today": today_stats,
        "kanji": kanji_items,
        "vocab": vocab_items,
        "grammar": unlocked_g,
        "locked_grammar": locked_g
    }
