#!/usr/bin/env python3
"""
core/anki_card_formatter.py — Card Field Formatter for Web SRS
Extracts front, reading, meaning, and notes into structured JSON payloads.
Strictly <= 200 lines, <= 100 cols invariant.
"""
import sqlite3
from typing import Any, Dict, List, Optional, Set

from core.anki_html_cleaner import clean_html
from core.anki_meanings_parser import extract_ruby_reading, parse_card_meanings
from core.anki_web_furigana import (
    build_ruby_representations,
    get_user_studied_kanji,
    resolve_furigana_segments,
    strip_ruby_to_text,
)


def _format_phonetic_fields(flds: List[str]):
    raw_front = flds[0] if len(flds) > 0 else ""
    m_raw = flds[1] if len(flds) > 1 else ""
    ruby_raw = flds[2] if len(flds) > 2 else ""
    p = parse_card_meanings(m_raw, extract_ruby_reading(ruby_raw))
    return raw_front, p["primary_reading"], p["primary_meaning"], "", ruby_raw, p["readings"]


def _format_kanji_image_fields(flds: List[str]):
    raw_front = flds[0] if len(flds) > 0 else ""
    notes = flds[1] if len(flds) > 1 else ""
    m_raw = flds[3] if len(flds) > 3 else notes
    p = parse_card_meanings(m_raw, "")
    return raw_front, p["primary_reading"], p["primary_meaning"], notes, "", p["readings"]


def _format_sentence_fields(flds: List[str]):
    raw_front = flds[0] if len(flds) > 0 else ""
    reading = flds[1] if len(flds) > 1 else ""
    notes = flds[2] if len(flds) > 2 else ""
    ruby_raw = reading
    from core.grammar_details_service import (
        format_grammar_html_for_card,
        lookup_grammar_for_sentence,
    )

    g_info = lookup_grammar_for_sentence(reading, raw_front, notes)
    meaning = format_grammar_html_for_card(g_info) if g_info else ""
    rule_name = g_info.get("title", "") if g_info else ""
    return raw_front, reading, meaning, notes, ruby_raw, [], rule_name


def format_card_data(
    mid: int,
    flds: List[str],
    dname: str,
    studied_kanji: Optional[Set[str]] = None,
    dict_conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    if studied_kanji is None:
        studied_kanji = get_user_studied_kanji()
    rule_name = ""
    readings: List[Dict[str, Any]] = []

    if mid == 1759962389887 or "Japanese -> Phonetic" in dname:
        raw_front, reading, meaning, notes, ruby_raw, readings = _format_phonetic_fields(flds)
    elif mid == 1607392319 or "Kanji - Image Deck" in dname:
        raw_front, reading, meaning, notes, ruby_raw, readings = _format_kanji_image_fields(flds)
    elif mid == 1758314923596 or "Kanji -> Writing" in dname:
        raw_front = flds[0] if len(flds) > 0 else ""
        reading = ""
        meaning = flds[1] if len(flds) > 1 else ""
        notes = ""
        ruby_raw = ""
    elif mid == 1771189232515 or "Jap Sentences" in dname:
        (
            raw_front, reading, meaning, notes,
            ruby_raw, readings, rule_name
        ) = _format_sentence_fields(flds)
    else:
        raw_front = flds[0] if len(flds) > 0 else "Carta"
        r_raw = flds[1] if len(flds) > 1 else ""
        m_raw = flds[2] if len(flds) > 2 else ""
        notes = flds[3] if len(flds) > 3 else ""
        p = parse_card_meanings(m_raw, r_raw)
        reading = p["primary_reading"] or r_raw
        meaning = p["primary_meaning"] or m_raw
        readings = p["readings"]
        ruby_raw = ""

    clean_front = strip_ruby_to_text(raw_front)
    is_phonetic = (
        mid == 1759962389887
        or "Japanese -> Phonetic" in dname
        or "Phonetic + Meaning" in dname
    )
    if is_phonetic:
        segments = resolve_furigana_segments(raw_front, reading, ruby_raw, dict_conn)
        ruby_all, ruby_unstudied = build_ruby_representations(segments, studied_kanji)
    else:
        ruby_all, ruby_unstudied = clean_front, clean_front

    return {
        "front": clean_html(clean_front),
        "ruby_all": clean_html(ruby_all) if ruby_all else clean_html(clean_front),
        "ruby_unstudied": (
            clean_html(ruby_unstudied) if ruby_unstudied else clean_html(clean_front)
        ),
        "reading": clean_html(reading),
        "meaning": clean_html(meaning),
        "notes": clean_html(notes),
        "readings": readings,
        "rule_name": rule_name,
    }
