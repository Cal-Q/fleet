#!/usr/bin/env python3
"""
engine/deep_sentence_matcher.py — Fast Sentence & Vocab Extractor for Bunpro Grammar
Pulls top 2 representative sentences per grammar point from bunpro_grammar_sentences.json.
Strictly <= 200 lines invariant.
"""

import json
import os
from typing import Any, Dict, List

BASE_DIR = "/opt/japan"
SENTENCES_FILE = os.path.join(BASE_DIR, "japanese", "bunpro_grammar_sentences.json")
_CACHE: Dict[str, Any] = {}


def load_sentences_db() -> Dict[str, Any]:
    global _CACHE
    if not _CACHE and os.path.exists(SENTENCES_FILE):
        with open(SENTENCES_FILE, "r", encoding="utf-8") as f:
            _CACHE = json.load(f)
    return _CACHE


def get_sentences_for_point(grammar_id: int, limit: int = 2) -> List[Dict[str, str]]:
    db = load_sentences_db()
    str_id = str(grammar_id)
    entry = db.get(str_id, {})
    if not entry:
        return []

    raw_sentences = entry.get("sentences", [])
    result = []

    for s in raw_sentences:
        clean_jp = s.get("plain_jp", "")
        clean_en = s.get("clean_en", "")
        audio = s.get("audio_url", None)
        if clean_jp and clean_en:
            result.append({
                "sentence_id": str(s.get("id", "")),
                "japanese": clean_jp,
                "english": clean_en,
                "audio_url": audio
            })
            if len(result) >= limit:
                break

    return result


def enrich_grammar_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    enriched = []
    for it in items:
        gid = it.get("id", 0)
        sentences = get_sentences_for_point(gid, limit=2)
        enriched.append({
            "id": gid,
            "title": it.get("title", ""),
            "meaning": it.get("meaning", ""),
            "url": it.get("url", f"https://bunpro.jp/grammar_points/{gid}"),
            "examples": sentences
        })
    return enriched


if __name__ == "__main__":
    db = load_sentences_db()
    print(f"Loaded {len(db)} grammar entries in sentences DB.")
    sample = get_sentences_for_point(146, limit=2)
    print(f"Sample sentences for grammar #146 (たところだ):")
    for s in sample:
        print(f"  JP: {s['japanese']}")
        print(f"  EN: {s['english']}")
