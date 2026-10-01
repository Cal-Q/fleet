#!/usr/bin/env python3
"""
engine/grammar_vocab_cache.py — Vocabulary and Grammar Cache Service
Provides loaded vocabulary sets, reviewed sets, and unstudied grammar lists.
Strictly <= 200 lines invariant.
"""

from datetime import datetime
import json
import os
import sys
from typing import Any, Dict, List, Set

from core.db import open_dict_db, open_anki_db, clean_kana

BASE_DIR = "/opt/japan"
DATA_DIR = os.path.join(BASE_DIR, "japanese")
VOCAB_FILE = os.path.join(DATA_DIR, "vocab_dict_filtered_all.json")
GRAMMAR_FILE = os.path.join(DATA_DIR, "bunpro_grammar_sentences.json")

LEVEL_ORDER = {
    "N5": 1,
    "N4": 2,
    "N3": 3,
    "N2": 4,
    "N1": 5,
    "Other": 6,
    "Hyōgai": 7,
}

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
    words = set()
    try:
        conn = open_dict_db(read_only=True)
        cur = conn.cursor()
        cur.execute("SELECT word, reading FROM jlpt_vocab WHERE in_anki = 1")
        for w, rd in cur.fetchall():
            if w:
                words.add(w.strip())
            if rd:
                words.add(rd.strip())
        try:
            cur.execute("SELECT kana FROM bunpro_vocab_queue")
            for r in cur.fetchall():
                if r[0]:
                    words.add(r[0].strip())
        except Exception:
            pass
        conn.close()
    except Exception as e:
        print(f"Error querying existing vocab words: {e}", file=sys.stderr)

    return words


def get_reviewed_vocab_set(refresh: bool = False) -> Set[str]:
    rev_set = set()
    try:
        conn = open_dict_db(read_only=True)
        cur = conn.cursor()
        cur.execute("SELECT kanji FROM kanji_catalog WHERE in_anki = 1")
        for r in cur.fetchall():
            if r[0]:
                rev_set.add(r[0].strip())
        cur.execute(
            "SELECT word, reading FROM jlpt_vocab WHERE in_anki = 1 AND status = 'studied'"
        )
        for w, rd in cur.fetchall():
            if w:
                rev_set.add(w.strip())
            if rd:
                rev_set.add(rd.strip())
        conn.close()
    except Exception as e:
        print(f"Error querying reviewed vocab from dict_index: {e}", file=sys.stderr)

    try:
        import re
        c_db = open_anki_db()
        c_cur = c_db.cursor()
        k_sql = (
            "SELECT n.flds FROM notes n JOIN cards c ON c.nid = n.id "
            "WHERE c.did IN (1757158925901, 1758314901201) AND c.reps > 0"
        )
        for (flds,) in c_cur.execute(k_sql):
            k = flds.split("\x1f")[0].strip()
            if len(k) == 1:
                rev_set.add(k)

        v_sql = (
            "SELECT n.flds FROM notes n JOIN cards c ON c.nid = n.id "
            "WHERE c.did = 1759999324396 AND c.reps > 0"
        )
        for (flds,) in c_cur.execute(v_sql):
            parts = flds.split("\x1f")
            w_raw = parts[0]
            clean_w = re.sub(r"<rt>.*?</rt>", "", w_raw)
            clean_w = clean_w.replace("<ruby>", "").replace("</ruby>", "").strip()
            if clean_w:
                rev_set.add(clean_w)
            m = re.findall(r"<rt>(.*?)</rt>", w_raw)
            if m:
                rev_set.add("".join(m))
            if len(parts) > 1 and parts[1]:
                clean_rd = clean_kana(parts[1], clean_w)
                if clean_rd:
                    rev_set.add(clean_rd)
        c_db.close()
    except Exception:
        pass

    return rev_set


def get_unstudied_grammar_points() -> List[Dict[str, Any]]:
    unstudied = []
    try:
        conn = open_dict_db(read_only=True)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, level, title, meaning, category, url
            FROM bunpro_grammar_points
            WHERE in_anki = 0
            ORDER BY id ASC
            """
        )
        for r in cur.fetchall():
            unstudied.append({
                "id": r[0],
                "level": r[1],
                "title": r[2],
                "meaning": r[3] or "",
                "category": r[4] or "",
                "url": r[5] or f"https://bunpro.jp/grammar_points/{r[0]}",
            })
        conn.close()
    except Exception as e:
        print(f"Error querying unstudied grammar points: {e}", file=sys.stderr)
    return unstudied
