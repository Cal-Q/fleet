#!/usr/bin/env python3
"""
engine/study_queue.py — Next Study Batch Provider
Returns upcoming Kanji, Vocabulary, and Grammar items with MEXT gating and priority.
Strictly <= 200 lines invariant.
"""

from datetime import datetime
import json
import os
import sys
from typing import Any, Dict, List, Set

from core.db import open_dict_db
from engine.grammar_vocab_gate import (
    get_grammar_priority_vocab,
    evaluate_grammar_queue,
    load_cached_json,
    LEVEL_ORDER,
)

BASE_DIR = "/opt/japan"
JAPANESE_DIR = os.path.join(BASE_DIR, "japanese")
DAILY_LOG_FILE = os.path.join(JAPANESE_DIR, "daily_additions.json")


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
        data[today] = {
            "date": today,
            "kanji": 0,
            "vocab": 0,
            "grammar": 0,
            "items": [],
        }

    data[today][category] = data[today].get(category, 0) + count
    for lbl in labels:
        data[today]["items"].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "category": category,
            "label": lbl,
        })

    with open(DAILY_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data[today]


def get_studied_kanji_set(refresh: bool = False) -> Set[str]:
    try:
        conn = open_dict_db(read_only=True)
        cur = conn.cursor()
        cur.execute("SELECT kanji FROM kanji_catalog WHERE in_anki = 1")
        res = {r[0] for r in cur.fetchall() if r[0]}
        conn.close()
        return res
    except Exception as e:
        print(f"Error querying studied kanji from dict_index: {e}", file=sys.stderr)
        return set()


def get_next_items(
    kanji_limit: int = 5,
    vocab_limit: int = 20,
    grammar_limit: int = 5,
) -> Dict[str, Any]:
    today_stats = load_daily_stats()

    # 1. VOCAB (Prioritizes unstudied vocab required by upcoming grammar rules)
    vocab_items = get_grammar_priority_vocab(
        vocab_limit=vocab_limit, grammar_limit=grammar_limit
    )
    priority_kanji = {
        c
        for v in vocab_items
        for c in v.get("word", "")
        if "\u4e00" <= c <= "\u9fff"
    }

    # 2. KANJI (Read directly from kanji_catalog in dict_index.sqlite3)
    kanji_items = []
    try:
        conn = open_dict_db(read_only=True)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, kanji, keyword, jlpt_level, on_reading, kun_reading,
                   main_on_reading
            FROM kanji_catalog
            WHERE in_anki = 0
            ORDER BY id ASC
            """
        )
        unstudied_k = [
            {
                "id": r[0],
                "kanji": r[1],
                "keyword": r[2],
                "jlpt_level": r[3],
                "on_reading": r[4] or "",
                "kun_reading": r[5] or "",
                "main_on_reading": r[6] or "",
            }
            for r in cur.fetchall()
        ]
        conn.close()
        unstudied_k.sort(
            key=lambda k: (
                0 if k["kanji"] in priority_kanji else 1,
                LEVEL_ORDER.get(k.get("jlpt_level", "Hyōgai"), 99),
                k["id"],
            )
        )
        kanji_items = unstudied_k[:kanji_limit]
    except Exception as e:
        print(f"Error querying next kanji from kanji_catalog: {e}", file=sys.stderr)

    # 3. GRAMMAR (Gated: only rules whose valid dictionary vocabularies have reps >= 1)
    unlocked_g, locked_g = evaluate_grammar_queue(grammar_limit=grammar_limit)

    return {
        "today": today_stats,
        "kanji": kanji_items,
        "vocab": vocab_items,
        "grammar": unlocked_g,
        "locked_grammar": locked_g,
    }
