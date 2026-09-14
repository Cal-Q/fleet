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

from core.db import open_anki_db, open_dict_db, ANKI_COLLECTION_PATH
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
    return {item["word"] for item in data if "word" in item} if isinstance(data, list) else (set(data.keys()) if isinstance(data, dict) else set())


def get_reviewed_vocab_set(refresh: bool = False) -> Set[str]:
    if not refresh and os.path.exists(REVIEWED_VOCAB_FILE):
        if not os.path.exists(ANKI_COLLECTION_PATH) or os.path.getmtime(REVIEWED_VOCAB_FILE) >= os.path.getmtime(ANKI_COLLECTION_PATH):
            cached = load_cached_json(REVIEWED_VOCAB_FILE)
            if isinstance(cached, list):
                return set(cached)

    try:
        col = open_anki_db()
        cur = col.cursor()
        rev_set = set()
        cur.execute("SELECT notes.flds FROM notes JOIN cards ON notes.id=cards.nid WHERE cards.did=1759999324396 AND cards.reps>0")
        for (flds,) in cur.fetchall():
            parts = flds.split(chr(31))
            raw = parts[0].strip()
            rev_set.add(raw)
            clean = re.sub(r'<[^>]+>', '', re.sub(r'<rt>.*?</rt>', '', raw, flags=re.DOTALL)).strip()
            rev_set.add(clean)
            if len(parts) > 1 and parts[1]:
                k_clean = re.sub(r'<[^>]+>', '', parts[1].split('<br>')[0]).strip()
                if k_clean:
                    rev_set.add(k_clean)

        cur.execute("SELECT notes.flds FROM notes JOIN cards ON notes.id=cards.nid WHERE cards.did=1757158925901 AND cards.reps>0")
        for (flds,) in cur.fetchall():
            parts = flds.split(chr(31))
            if parts[0].strip():
                rev_set.add(parts[0].strip()[0])
            if len(parts) > 3 and parts[3]:
                k_clean = re.sub(r'<[^>]+>', '', parts[3].split('<br>')[0]).strip()
                if k_clean:
                    rev_set.add(k_clean)
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
    return [p for pts in gp_data.get("unstudied_by_level", {}).values() for p in pts]


def evaluate_grammar_queue(grammar_limit: int = 5) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    unstudied = get_unstudied_grammar_points()
    if not unstudied:
        return [], []
    unstudied.sort(key=grammar_sort_key)

    reviewed_vocab = get_reviewed_vocab_set()
    sent_data = load_cached_json(GRAMMAR_FILE)
    sent_map = {x.get("id", k): x.get("sentences", []) for k, x in (sent_data.items() if isinstance(sent_data, dict) else [(i.get("id"), i) for i in sent_data])}

    dict_conn = open_dict_db()
    dict_cur = dict_conn.cursor()
    unlocked, locked = [], []

    try:
        from collections import defaultdict
        dict_cur.execute("SELECT grammar_id, title FROM bunpro_grammar_vocab_coverage")
        cov_by_gid = defaultdict(list)
        for gid, title in dict_cur.fetchall():
            cov_by_gid[gid].append(title)

        for g in unstudied:
            gid = g.get("id")
            cov_words = cov_by_gid.get(gid, [])
            sents = sent_map.get(gid, [])[:5]
            sent_text = " ".join((s.get("plain_jp", "") + " " + s.get("clean_jp", "")) for s in sents)
            active_words = [w for w in cov_words if w in sent_text]
            missing = [w for w in active_words if w not in reviewed_vocab]

            item = dict(g)
            item["required_vocab_count"] = len(active_words)
            item["missing_vocab"] = missing
            item["unreviewed_vocab_count"] = len(missing)
            item["unreviewed_vocab_samples"] = missing[:5]
            item["cluster"] = classify_mext_cluster(g)
            item["sentences"] = sents

            if not missing:
                unlocked.append(item)
            else:
                locked.append(item)

        return unlocked[:grammar_limit], locked[:grammar_limit]
    finally:
        dict_conn.close()


def get_grammar_priority_vocab(vocab_limit: int = 20) -> List[Dict[str, Any]]:
    unstudied = get_unstudied_grammar_points()
    if not unstudied:
        return []
    unstudied.sort(key=grammar_sort_key)
    existing_words = get_existing_vocab_words()
    reviewed_vocab = get_reviewed_vocab_set()
    sent_data = load_cached_json(GRAMMAR_FILE)
    sent_map = {x.get("id", k): x.get("sentences", []) for k, x in (sent_data.items() if isinstance(sent_data, dict) else [(i.get("id"), i) for i in sent_data])}

    dict_conn = open_dict_db()
    dict_cur = dict_conn.cursor()
    priority_items = []
    seen = set()

    try:
        from collections import defaultdict
        dict_cur.execute("SELECT grammar_id, title, furigana, meaning, level FROM bunpro_grammar_vocab_coverage")
        cov_by_gid = defaultdict(list)
        for r in dict_cur.fetchall():
            cov_by_gid[r[0]].append(dict(r))

        for g in unstudied:
            gid = g.get("id")
            cov_items = cov_by_gid.get(gid, [])
            sents = sent_map.get(gid, [])[:5]
            sent_text = " ".join((s.get("plain_jp", "") + " " + s.get("clean_jp", "")) for s in sents)
            active = [c for c in cov_items if c["title"] in sent_text]
            for c in active:
                word = c["title"]
                if word in existing_words or word in reviewed_vocab or word in seen:
                    continue
                seen.add(word)
                priority_items.append({
                    "word": word, "reading": c.get("furigana") or word, "level": c.get("level") or g.get("level", "N3"),
                    "meaning": c.get("meaning") or "Grammar prerequisite vocabulary",
                    "source": f"Bunpro: {g.get('title', '')}",
                    "priority": True, "required_by_grammar": True
                })
                if len(priority_items) >= vocab_limit:
                    return priority_items

        for v in (load_cached_json(VOCAB_FILE) or []):
            w = v.get("word", "")
            if w and w not in existing_words and w not in seen:
                seen.add(w)
                priority_items.append(v)
                if len(priority_items) >= vocab_limit:
                    break

        return priority_items
    finally:
        dict_conn.close()
