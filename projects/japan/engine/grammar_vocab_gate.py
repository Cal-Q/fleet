#!/usr/bin/env python3
"""
engine/grammar_vocab_gate.py — Vocab-First Prerequisite & Grammar Gating Service
Enforces comprehensible input: grammar sentences are hidden/suspended until all
valid dictionary vocabularies have been reviewed >= 1 time in Anki.
Strictly <= 200 lines invariant.
"""

from collections import defaultdict
import os
import sys
from typing import Any, Dict, List, Tuple

from core.db import open_dict_db, clean_kana
from engine.grammar_clusters import classify_mext_cluster, grammar_sort_key
from engine.grammar_vocab_cache import (
    LEVEL_ORDER,
    load_cached_json,
    get_existing_vocab_words,
    get_reviewed_vocab_set,
    get_unstudied_grammar_points,
)

BASE_DIR = "/opt/japan"
DATA_DIR = os.path.join(BASE_DIR, "japanese")
VOCAB_FILE = os.path.join(DATA_DIR, "vocab_dict_filtered_all.json")
GRAMMAR_FILE = os.path.join(DATA_DIR, "bunpro_grammar_sentences.json")


def evaluate_grammar_queue(
    grammar_limit: int = 5,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    unstudied = get_unstudied_grammar_points()
    if not unstudied:
        return [], []
    unstudied.sort(key=grammar_sort_key)

    reviewed_vocab = get_reviewed_vocab_set()
    sent_data = load_cached_json(GRAMMAR_FILE) or {}
    dict_conn = open_dict_db()
    dict_conn.row_factory = None
    dict_cur = dict_conn.cursor()

    try:
        gids = [g.get("id") for g in unstudied[:grammar_limit] if g.get("id")]
        cov_by_gid = defaultdict(list)
        if gids:
            ph = ",".join("?" * len(gids))
            try:
                dict_cur.execute(
                    f"SELECT grammar_id, title, furigana "
                    f"FROM bunpro_grammar_vocab_coverage WHERE grammar_id IN ({ph})",
                    gids,
                )
                for gid, title, furi in dict_cur.fetchall():
                    cov_by_gid[gid].append((title, furi))
            except Exception as e:
                print(f"Warning querying grammar coverage: {e}", file=sys.stderr)

        next_batch = []
        for g in unstudied[:grammar_limit]:
            gid = g.get("id")
            cov_words = cov_by_gid.get(gid, [])
            missing = [
                w
                for w, furi in cov_words
                if w not in reviewed_vocab and clean_kana(furi, w) not in reviewed_vocab
            ]
            item = dict(g)
            item["required_vocab_count"] = len(cov_words)
            item["missing_vocab"] = [w for w, _ in cov_words if w in missing]
            item["unreviewed_vocab_count"] = len(missing)
            item["unreviewed_vocab_samples"] = [
                w for w, _ in cov_words if w in missing
            ][:5]
            item["is_locked"] = len(missing) > 0
            item["cluster"] = classify_mext_cluster(g)
            raw_s = sent_data.get(str(gid)) or sent_data.get(gid) or {}
            item["sentences"] = (
                (raw_s.get("sentences") or [])[:5] if isinstance(raw_s, dict) else []
            )
            next_batch.append(item)

        is_any_locked = any(it["is_locked"] for it in next_batch)
        if is_any_locked:
            return [], next_batch
        return next_batch, []
    finally:
        dict_conn.close()


def _is_word_excluded(
    word: str,
    furigana: str,
    reviewed: set,
    existing: set,
    seen: set,
) -> bool:
    ck = clean_kana(furigana, word)
    if word in reviewed or ck in reviewed:
        return True
    if word in existing or ck in existing:
        return True
    return word in seen


def get_grammar_priority_vocab(
    vocab_limit: int = 20,
    grammar_limit: int = 5,
) -> List[Dict[str, Any]]:
    unstudied = get_unstudied_grammar_points()
    unstudied.sort(key=grammar_sort_key)
    existing_words = get_existing_vocab_words()
    reviewed_vocab = get_reviewed_vocab_set()
    dict_conn = open_dict_db()
    dict_conn.row_factory = None
    dict_cur = dict_conn.cursor()
    priority_items = []
    seen = set()

    try:
        all_gids = [g.get("id") for g in unstudied if g.get("id")]
        cov_by_gid = defaultdict(list)
        if all_gids:
            ph = ",".join("?" * len(all_gids))
            try:
                dict_cur.execute(
                    f"SELECT grammar_id, title, furigana, meaning, level "
                    f"FROM bunpro_grammar_vocab_coverage WHERE grammar_id IN ({ph})",
                    all_gids,
                )
                for gid, w, furi, mean, lvl in dict_cur.fetchall():
                    cov_by_gid[gid].append((w, furi, mean, lvl))
            except Exception as e:
                print(f"Warning querying grammar priority vocab: {e}", file=sys.stderr)

        for g in unstudied[:grammar_limit]:
            gid = g.get("id")
            for w, furi, mean, lvl in cov_by_gid.get(gid, []):
                if _is_word_excluded(w, furi, reviewed_vocab, existing_words, seen):
                    continue
                seen.add(w)
                priority_items.append({
                    "word": w,
                    "reading": furi or w,
                    "level": lvl or "N4",
                    "meaning": mean or "Prerequisito Bunpro",
                    "source": f"Prerequisito bloccante: #{gid}",
                    "priority": True,
                    "required_by_grammar": True,
                    "req_type": "blocking",
                })
                if len(priority_items) >= vocab_limit:
                    return priority_items

        for g in unstudied[grammar_limit:]:
            gid = g.get("id")
            for w, furi, mean, lvl in cov_by_gid.get(gid, []):
                if _is_word_excluded(w, furi, reviewed_vocab, existing_words, seen):
                    continue
                seen.add(w)
                priority_items.append({
                    "word": w,
                    "reading": furi or w,
                    "level": lvl or "N4",
                    "meaning": mean or "Vocabolario futuro",
                    "source": f"Grammatica futura: #{gid}",
                    "priority": False,
                    "required_by_grammar": False,
                    "req_type": "consolidation",
                })
                if len(priority_items) >= vocab_limit:
                    return priority_items

        if len(priority_items) < vocab_limit:
            vocab_list = load_cached_json(VOCAB_FILE) or []
            for v in vocab_list:
                w = v.get("word", "")
                if not w or w in existing_words or w in seen or w in reviewed_vocab:
                    continue
                seen.add(w)
                v_copy = dict(v)
                v_copy["req_type"] = "consolidation"
                priority_items.append(v_copy)
                if len(priority_items) >= vocab_limit:
                    break
        return priority_items
    finally:
        dict_conn.close()
