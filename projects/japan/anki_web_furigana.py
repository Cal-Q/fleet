#!/usr/bin/env python3
"""
core/anki_web_furigana.py — Furigana & Ruby Engine for AnkiWeb
Resolves ruby segments and filters furigana for unstudied/unknown kanji.
Strictly <= 200 lines invariant.
"""
import json
import os
import re
import time
import urllib.parse
from typing import Any, Dict, List, Optional, Set, Tuple
import sqlite3
from core.db import open_dict_db, open_anki_db
from core.anki_meanings_parser import extract_ruby_reading, parse_card_meanings

_STUDIED_CACHE: Set[str] = set()
_STUDIED_CACHE_TIME: float = 0.0


def get_user_studied_kanji(max_age_sec: float = 60.0) -> Set[str]:
    """Returns set of genuine kanji characters studied by user."""
    global _STUDIED_CACHE, _STUDIED_CACHE_TIME
    now = time.time()
    if _STUDIED_CACHE and (now - _STUDIED_CACHE_TIME < max_age_sec):
        return _STUDIED_CACHE
    try:
        col = open_anki_db()
        cur = col.cursor()
        cur.execute("""
            SELECT DISTINCT SUBSTR(n.flds, 1, 1)
            FROM cards c JOIN notes n ON c.nid = n.id
            WHERE (c.did = 1757158925901 AND c.reps > 1)
               OR (c.did = 1758314901201 AND c.reps > 0)
        """)
        res = {r[0] for r in cur.fetchall() if r[0] and "\u4e00" <= r[0] <= "\u9faf"}
        col.close()
        _STUDIED_CACHE, _STUDIED_CACHE_TIME = res, now
        return res
    except Exception:
        return _STUDIED_CACHE if _STUDIED_CACHE else set()


def strip_ruby_to_text(html: str) -> str:
    if not html:
        return ""
    t = re.sub(r"<(rt|rp|style)[\s\S]*?</\1>", "", html)
    return re.sub(r"<[^>]+>", "", t).strip()


def clean_html(raw: str) -> str:
    if not raw:
        return ""
    text = re.sub(r"<style[\s\S]*?</style>", "", raw).strip()
    def fix_img(m):
        src = m.group(1).strip()
        if not src.startswith("http://") and not src.startswith("https://") and not src.startswith("/"):
            src = f"/media/{urllib.parse.quote(src)}"
        return f'<img src="{src}" loading="lazy" decoding="async" class="max-h-56 max-w-full mx-auto rounded my-2 object-contain inline-block shadow-md">'
    text = re.sub(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', fix_img, text)
    def fix_sound(m):
        s_file = urllib.parse.quote(m.group(1).strip())
        return f'<button type="button" onclick="event.stopPropagation();window.ankiPlayAudio(\'/media/{s_file}\')" class="inline-flex items-center gap-1.5 px-3 py-1 bg-[#2C2C2C] hover:bg-[#3C3C3C] rounded-full text-xs font-mono text-white transition tap-press my-1 border border-[#3C3C3C] shadow"><span class="text-[#42A5F5]">▶</span> <span>Audio</span></button>'
    return re.sub(r'\[sound:([^\]]+)\]', fix_sound, text)


def parse_existing_ruby(ruby_html: str) -> Optional[List[Tuple[str, Optional[str]]]]:
    if not ruby_html or "<ruby" not in ruby_html:
        return None
    src = re.split(r"<br\s*/?>|\n", ruby_html, maxsplit=1)[0].strip()
    tokens, pos, pattern = [], 0, re.compile(r"<ruby>([^<]+)<rt>([^<]*)</rt></ruby>")
    for match in pattern.finditer(src):
        start, end = match.span()
        if start > pos:
            clean_before = strip_ruby_to_text(src[pos:start])
            if clean_before:
                tokens.append((clean_before, None))
        rt_val = match.group(2).strip()
        tokens.append((match.group(1), rt_val if rt_val else None))
        pos = end
    if pos < len(src):
        clean_after = strip_ruby_to_text(src[pos:])
        if clean_after:
            tokens.append((clean_after, None))
    return tokens if tokens else None


def align_kana_fallback(text: str, reading: str) -> List[Tuple[str, Optional[str]]]:
    if not text or not reading or text == reading:
        return [(text, None)]
    prefix_len, suffix_len = 0, 0
    while prefix_len < len(text) and prefix_len < len(reading) and text[prefix_len] == reading[prefix_len]:
        prefix_len += 1
    while (suffix_len < (len(text) - prefix_len) and suffix_len < (len(reading) - prefix_len)
           and text[len(text) - 1 - suffix_len] == reading[len(reading) - 1 - suffix_len]):
        suffix_len += 1
    prefix = text[:prefix_len]
    suffix = text[len(text) - suffix_len:] if suffix_len > 0 else ""
    mid_t = text[prefix_len:len(text) - suffix_len] if suffix_len > 0 else text[prefix_len:]
    mid_r = reading[prefix_len:len(reading) - suffix_len] if suffix_len > 0 else reading[prefix_len:]
    segments = []
    if prefix: segments.append((prefix, None))
    if mid_t: segments.append((mid_t, mid_r if mid_r else None))
    if suffix: segments.append((suffix, None))
    return segments


def resolve_furigana_segments(text: str, reading: str, existing_ruby: str = "", dict_conn: Optional[sqlite3.Connection] = None) -> List[Tuple[str, Optional[str]]]:
    clean_t = strip_ruby_to_text(text)
    clean_r = strip_ruby_to_text(reading)
    if not clean_t:
        return []
    conn = dict_conn or open_dict_db()
    try:
        cur = conn.cursor()
        if clean_r:
            cur.execute("SELECT segments FROM furigana WHERE text = ? AND reading = ? LIMIT 1", (clean_t, clean_r))
        else:
            cur.execute("SELECT segments FROM furigana WHERE text = ? LIMIT 1", (clean_t,))
        row = cur.fetchone()
        if row and row[0]:
            return [(s, rt) for s, rt in json.loads(row[0])]
    except Exception:
        pass
    finally:
        if dict_conn is None:
            conn.close()
    parsed = parse_existing_ruby(existing_ruby) or parse_existing_ruby(text)
    if parsed:
        parsed_r = "".join(rt if rt else s for s, rt in parsed)
        if not clean_r or parsed_r == clean_r:
            return parsed
    return align_kana_fallback(clean_t, clean_r)


def build_ruby_representations(segments: List[Tuple[str, Optional[str]]], studied_kanji: Set[str]) -> Tuple[str, str]:
    ruby_all_parts, ruby_unstudied_parts = [], []
    for s, rt in segments:
        if not rt:
            ruby_all_parts.append(s); ruby_unstudied_parts.append(s)
        else:
            ruby_all_parts.append(f"<ruby>{s}<rt>{rt}</rt></ruby>")
            kanjis = [ch for ch in s if "\u4e00" <= ch <= "\u9faf"]
            if kanjis and all(k in studied_kanji for k in kanjis):
                ruby_unstudied_parts.append(s)
            else:
                ruby_unstudied_parts.append(f"<ruby>{s}<rt>{rt}</rt></ruby>")
    return "".join(ruby_all_parts), "".join(ruby_unstudied_parts)


def format_card_data(mid: int, flds: List[str], dname: str, studied_kanji: Optional[Set[str]] = None, dict_conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    if studied_kanji is None: studied_kanji = get_user_studied_kanji()
    raw_front, reading, meaning, notes, ruby_raw, hint_html, rule_name = "", "", "", "", "", "", ""
    readings: List[Dict[str, Any]] = []
    if mid == 1759962389887 or "Japanese -> Phonetic" in dname:
        raw_front = flds[0] if len(flds) > 0 else ""
        m_raw, ruby_raw = (flds[1] if len(flds) > 1 else ""), (flds[2] if len(flds) > 2 else "")
        p = parse_card_meanings(m_raw, extract_ruby_reading(ruby_raw))
        reading, meaning, readings = p["primary_reading"], p["primary_meaning"], p["readings"]
    elif mid == 1607392319 or "Kanji - Image Deck" in dname:
        raw_front, notes = (flds[0] if len(flds) > 0 else ""), (flds[1] if len(flds) > 1 else "")
        m_raw = flds[3] if len(flds) > 3 else (flds[1] if len(flds) > 1 else "")
        p = parse_card_meanings(m_raw, "")
        reading, meaning, readings = p["primary_reading"], p["primary_meaning"], p["readings"]
    elif mid == 1758314923596 or "Kanji -> Writing" in dname:
        raw_front, meaning = (flds[0] if len(flds) > 0 else ""), (flds[1] if len(flds) > 1 else "")
    elif mid == 1771189232515 or "Jap Sentences" in dname:
        raw_front, reading, notes, ruby_raw = (flds[0] if len(flds) > 0 else ""), (flds[1] if len(flds) > 1 else ""), (flds[2] if len(flds) > 2 else ""), (flds[1] if len(flds) > 1 else "")
        from core.grammar_details_service import lookup_grammar_for_sentence, format_grammar_html_for_card
        g_info = lookup_grammar_for_sentence(reading, raw_front, notes)
        if g_info:
            meaning = format_grammar_html_for_card(g_info)
            rule_name = g_info.get("title", "")
    else:
        raw_front, r_raw = (flds[0] if len(flds) > 0 else "Carta"), (flds[1] if len(flds) > 1 else "")
        m_raw, notes = (flds[2] if len(flds) > 2 else ""), (flds[3] if len(flds) > 3 else "")
        p = parse_card_meanings(m_raw, r_raw)
        reading, meaning, readings = p["primary_reading"] or r_raw, p["primary_meaning"] or m_raw, p["readings"]

    clean_front = strip_ruby_to_text(raw_front)
    is_phonetic_deck = (mid == 1759962389887 or "Japanese -> Phonetic" in dname or "Phonetic + Meaning" in dname)
    if is_phonetic_deck:
        segments = resolve_furigana_segments(raw_front, reading, ruby_raw, dict_conn)
        ruby_all, ruby_unstudied = build_ruby_representations(segments, studied_kanji)
    else:
        ruby_all, ruby_unstudied = clean_front, clean_front

    return {
        "front": clean_html(clean_front),
        "ruby_all": clean_html(ruby_all) if ruby_all else clean_html(clean_front),
        "ruby_unstudied": clean_html(ruby_unstudied) if ruby_unstudied else clean_html(clean_front),
        "reading": clean_html(reading), "meaning": clean_html(meaning), "notes": clean_html(notes),
        "readings": readings, "rule_name": rule_name
    }
