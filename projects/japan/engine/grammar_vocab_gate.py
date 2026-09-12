#!/usr/bin/env python3
"""
engine/grammar_vocab_gate.py — Vocab-First Prerequisite & Grammar Gating Service
Enforces comprehensible input: grammar sentences are hidden/suspended until all
valid dictionary vocabularies have been reviewed >= 1 time in Anki.
Strictly <= 200 lines invariant.
"""

import json
import os
import re
import sys
from typing import Any, Dict, List, Set, Tuple

from core.db import open_anki_db, open_dict_db
from engine.grammar_clusters import classify_mext_cluster, grammar_sort_key

BASE_DIR = "/opt/japan"
DATA_DIR = os.path.join(BASE_DIR, "japanese")
VOCAB_FILE = os.path.join(DATA_DIR, "vocab_dict_filtered_all.json")
USER_VOCAB_FILE = os.path.join(DATA_DIR, "user_anki_vocab.json")
REVIEWED_VOCAB_FILE = os.path.join(DATA_DIR, "user_reviewed_vocab.json")
GRAMMAR_FILE = os.path.join(DATA_DIR, "bunpro_grammar_sentences.json")
GRAMMAR_PROGRESS_FILE = os.path.join(DATA_DIR, "grammar_progress.json")

LEVEL_ORDER = {"N5": 1, "N4": 2, "N3": 3, "N2": 4, "N1": 5, "Other": 6, "Hyōgai": 7}

_JSON_CACHE: Dict[str, Any] = {}
_JSON_MTIMES: Dict[str, float] = {}


def load_cached_json(path: str) -> Any:
    if not os.path.exists(path):
        return {}
    mtime = os.path.getmtime(path)
    if path not in _JSON_CACHE or mtime != _JSON_MTIMES.get(path, 0.0):
        try:
            with open(path, "r", encoding="utf-8") as f:
                _JSON_CACHE[path] = json.load(f)
            _JSON_MTIMES[path] = mtime
        except Exception:
            return {}
    return _JSON_CACHE[path]


def get_existing_vocab_words() -> Set[str]:
    data = load_cached_json(USER_VOCAB_FILE)
    if isinstance(data, list):
        return {item["word"] for item in data if "word" in item}
    return set(data.keys()) if isinstance(data, dict) else set()


def get_reviewed_vocab_set(refresh: bool = False) -> Set[str]:
    if not refresh and os.path.exists(REVIEWED_VOCAB_FILE):
        cached = load_cached_json(REVIEWED_VOCAB_FILE)
        if isinstance(cached, list):
            return set(cached)

    try:
        col = open_anki_db()
        cur = col.cursor()
        cur.execute("""
            SELECT notes.flds 
            FROM notes 
            JOIN cards ON notes.id=cards.nid 
            WHERE cards.did=1759999324396 AND cards.reps>0
        """)
        rev_set = set()
        for (flds,) in cur.fetchall():
            raw = flds.split(chr(31))[0].strip()
            rev_set.add(raw)
            clean = re.sub(r'<[^>]+>', '', raw).strip()
            rev_set.add(clean)
        col.close()

        with open(REVIEWED_VOCAB_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(rev_set)), f, ensure_ascii=False)
        return rev_set
    except Exception as e:
        print(f"Error querying reviewed vocab from local Anki: {e}", file=sys.stderr)
        return set()


def get_unstudied_grammar_points() -> List[Dict[str, Any]]:
    gp_data = load_cached_json(GRAMMAR_PROGRESS_FILE)
    if not gp_data:
        return []
    unstudied = []
    for _lvl, pts in gp_data.get("unstudied_by_level", {}).items():
        for p in pts:
            unstudied.append(p)
    return unstudied


def evaluate_grammar_queue(grammar_limit: int = 5) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    unstudied = get_unstudied_grammar_points()
    if not unstudied:
        return [], []

    reviewed_vocab = get_reviewed_vocab_set()
    dict_conn = open_dict_db()
    dict_cur = dict_conn.cursor()

    unlocked = []
    locked = []

    try:
        for g in unstudied:
            gid = g.get("id")
            dict_cur.execute("SELECT title FROM bunpro_grammar_vocab_coverage WHERE grammar_id = ?", (gid,))
            titles = [r[0] for r in dict_cur.fetchall()]
            valid_words = [
                t for t in titles 
                if dict_cur.execute("SELECT 1 FROM furigana WHERE text = ? LIMIT 1", (t,)).fetchone() 
                or dict_cur.execute("SELECT 1 FROM reading_elements WHERE reading = ? LIMIT 1", (t,)).fetchone()
            ]
            missing = [w for w in valid_words if w not in reviewed_vocab]

            item = dict(g)
            item["required_vocab_count"] = len(valid_words)
            item["missing_vocab"] = missing
            item["cluster"] = classify_mext_cluster(g)

            if not missing:
                unlocked.append(item)
            else:
                locked.append(item)

        unlocked.sort(key=grammar_sort_key)
        locked.sort(key=grammar_sort_key)

        return unlocked[:grammar_limit], locked[:grammar_limit]
    finally:
        dict_conn.close()


def get_grammar_priority_vocab(vocab_limit: int = 20) -> List[Dict[str, Any]]:
    unstudied = get_unstudied_grammar_points()
    existing_words = get_existing_vocab_words()
    reviewed_vocab = get_reviewed_vocab_set()

    dict_conn = open_dict_db()
    dict_cur = dict_conn.cursor()

    priority_items = []
    seen = set()

    try:
        for g in unstudied:
            gid = g.get("id")
            dict_cur.execute("""
                SELECT title, furigana, meaning, level 
                FROM bunpro_grammar_vocab_coverage 
                WHERE grammar_id = ?
            """, (gid,))
            for r in dict_cur.fetchall():
                word, reading, meaning, lvl = r[0], r[1], r[2], r[3]
                if word in existing_words or word in reviewed_vocab or word in seen:
                    continue
                seen.add(word)
                priority_items.append({
                    "word": word,
                    "reading": reading or word,
                    "meaning": meaning or "Grammar prerequisite vocabulary",
                    "level": lvl or g.get("level", "N3"),
                    "source": f"Bunpro Grammar Prerequisite: {g.get('title', '')}",
                    "priority": True
                })
                if len(priority_items) >= vocab_limit:
                    return priority_items

        # Fill remaining slots with normal curriculum
        vocab_all = load_cached_json(VOCAB_FILE)
        if isinstance(vocab_all, list):
            for v in vocab_all:
                w = v.get("word", "")
                if w and w not in existing_words and w not in seen:
                    seen.add(w)
                    priority_items.append(v)
                    if len(priority_items) >= vocab_limit:
                        break

        return priority_items
    finally:
        dict_conn.close()
