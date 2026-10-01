"""
core/grammar_details_service.py — Bunpro Grammar Details Lookup Service.

Indexes Bunpro grammar points and sentences to provide instant O(1) enrichment
for sentence flashcards during study sessions.
Strictly <= 200 lines invariant.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("grammar_service")

_DETAILS_CACHE: Optional[Dict[str, Any]] = None
_JP_INDEX: Dict[str, int] = {}
_EN_INDEX: Dict[str, int] = {}
_AUDIO_INDEX: Dict[str, int] = {}


def _clean_jp(html: str) -> str:
    """Strip ruby rt/rp tags and HTML tags, returning plain text."""
    no_rt = re.sub(r"<r[tp]>[^<]*</r[tp]>", "", html)
    clean = re.sub(r"<[^>]+>", "", no_rt)
    return re.sub(r"[\s\u3000\.,!?。、！？\(\)（）]", "", clean)


def _clean_en(text: str) -> str:
    """Normalize English sentence for relaxed matching."""
    clean = re.sub(r"<[^>]+>", "", text).lower().strip()
    return re.sub(r"[\s\.,!?\(\)（）\"\']", "", clean)


def _find_data_file(filename: str) -> Optional[Path]:
    for p in [
        Path(__file__).resolve().parent.parent / "japanese" / filename,
        Path("/opt/japan/japanese") / filename,
        Path("japanese") / filename,
    ]:
        if p.exists():
            return p
    return None


def init_grammar_service() -> bool:
    """Load grammar details and sentences index into memory."""
    global _DETAILS_CACHE, _JP_INDEX, _EN_INDEX, _AUDIO_INDEX
    if _DETAILS_CACHE is not None:
        return True

    det_path = _find_data_file("bunpro_grammar_details.json")
    sent_path = _find_data_file("bunpro_grammar_sentences.json")
    if not det_path or not sent_path:
        return False

    try:
        with open(det_path, "r", encoding="utf-8") as f:
            _DETAILS_CACHE = json.load(f)
        with open(sent_path, "r", encoding="utf-8") as f:
            sentences_db = json.load(f)

        for gp_id_str, gp in sentences_db.items():
            try:
                gp_id = int(gp_id_str)
            except ValueError:
                continue
            for s in gp.get("sentences", []):
                c_jp = _clean_jp(s.get("clean_jp", ""))
                if c_jp:
                    _JP_INDEX[c_jp] = gp_id
                a_url = s.get("audio_url", "")
                if a_url:
                    _AUDIO_INDEX[a_url.split("/")[-1]] = gp_id
                c_en = _clean_en(s.get("clean_en", ""))
                if c_en:
                    _EN_INDEX[c_en] = gp_id
        return True
    except Exception as exc:
        logger.error(f"Failed to initialize grammar service: {exc}")
        return False


def get_grammar_details_by_id(gp_id: int) -> Optional[Dict[str, Any]]:
    """Return grammar details dictionary by ID."""
    if _DETAILS_CACHE is None and not init_grammar_service():
        return None
    return _DETAILS_CACHE.get(str(gp_id)) if _DETAILS_CACHE else None


def lookup_grammar_for_sentence(jp_raw: str, en_raw: str = "", audio_raw: str = "") -> Optional[Dict[str, Any]]:
    """Match a sentence card against grammar rules via SQLite or memory index."""
    c_jp, c_en = _clean_jp(jp_raw), _clean_en(en_raw)
    try:
        from core.db import open_dict_db
        conn = open_dict_db(read_only=True)
        cur = conn.cursor()
        target_gid = None
        if c_en:
            cur.execute("SELECT grammar_id FROM bunpro_grammar_sentences WHERE clean_en = ? LIMIT 1", (c_en,))
            r = cur.fetchone()
            if r: target_gid = r["grammar_id"]
        if not target_gid and c_jp:
            cur.execute("SELECT grammar_id FROM bunpro_grammar_sentences WHERE clean_jp = ? LIMIT 1", (c_jp,))
            r = cur.fetchone()
            if r: target_gid = r["grammar_id"]
        if target_gid:
            cur.execute("SELECT * FROM bunpro_grammar_details WHERE id = ?", (target_gid,))
            d = cur.fetchone()
            if d:
                conn.close()
                return dict(d)
        conn.close()
    except Exception:
        pass

    if _DETAILS_CACHE is None and not init_grammar_service():
        return None
    gp_id = _JP_INDEX.get(c_jp)
    if gp_id:
        return _DETAILS_CACHE.get(str(gp_id))
    for line in jp_raw.split("<br>"):
        sub_c = _clean_jp(line)
        if sub_c in _JP_INDEX:
            return _DETAILS_CACHE.get(str(_JP_INDEX[sub_c]))
    if en_raw and c_en in _EN_INDEX:
        return _DETAILS_CACHE.get(str(_EN_INDEX[c_en]))
    if audio_raw:
        m = re.search(r"bunpro_[^\"\']+\.mp3", audio_raw)
        if m and m.group(0) in _AUDIO_INDEX:
            return _DETAILS_CACHE.get(str(_AUDIO_INDEX[m.group(0)]))
    return None


def format_sentence_hint(details: Dict[str, Any]) -> str:
    """Format subtle situational context badge for English -> JP sentence cards (Solution A)."""
    if not details:
        return ""
    nuance = details.get("nuance", "")
    meaning = details.get("meaning", "")
    clean_nuance = re.sub(r"<[^>]+>", "", nuance).strip() if nuance else ""
    if clean_nuance:
        short = clean_nuance.split(".")[0].strip()
        hint_text = (short[:57] + "...") if len(short) > 60 else short
    elif meaning:
        hint_text = meaning
    else:
        return ""
    return (
        f'<div class="mt-2 text-center">'
        f'<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full '
        f'bg-[#1E3A8A]/40 border border-[#2563EB]/40 text-[#93C5FD] text-[11px] font-mono shadow-sm">'
        f'💡 <b>Context:</b> {hint_text}</span></div>'
    )


def format_grammar_html_for_card(details: Dict[str, Any]) -> str:
    """Format rich Bunpro grammar details into dark-mode styled HTML."""
    if not details:
        return ""

    title = details.get("title", "")
    meaning = details.get("meaning", "")
    level = details.get("level", "N/A")
    pos = details.get("part_of_speech", "")
    wtype = details.get("word_type", "")
    structure = details.get("structure", "")
    caution = details.get("caution", "")
    about = details.get("about_html", "")

    badges = [f'<span class="px-2 py-0.5 rounded-md bg-[#2563EB]/25 text-[#60A5FA] border border-[#2563EB]/40 font-mono text-[10px] font-bold uppercase">{level}</span>']
    if pos:
        badges.append(f'<span class="px-2 py-0.5 rounded-md bg-neutral-800 text-neutral-300 border border-neutral-700 text-[10px] font-medium">{pos}</span>')
    if wtype and wtype != pos:
        badges.append(f'<span class="px-2 py-0.5 rounded-md bg-neutral-800 text-neutral-400 border border-neutral-700 text-[10px] font-medium">{wtype}</span>')
    badges_html = f'<div class="flex flex-wrap items-center gap-1.5 mb-2.5">{"".join(badges)}</div>'

    header = f'<div class="mb-3"><div class="text-base sm:text-lg font-bold text-white jp-font">{title}</div><div class="text-xs text-neutral-300 mt-0.5">{meaning}</div></div>'
    
    struct_html = ""
    if structure:
        struct_html = f'<div class="mb-3 p-2.5 rounded-xl bg-[#1A1A1A] border border-[#2E2E2E]"><div class="text-[10px] font-mono uppercase tracking-wider text-neutral-400 mb-1 font-semibold">Structure</div><div class="text-xs sm:text-sm text-neutral-200 jp-font">{structure}</div></div>'

    caution_html = ""
    if caution:
        caution_html = f'<div class="mb-3 p-2.5 rounded-xl bg-[#2D1A10] border border-[#D97706]/40 text-left"><div class="text-[10px] font-mono uppercase tracking-wider text-[#F59E0B] font-bold mb-1 flex items-center gap-1"><span>⚠️</span> Caution</div><div class="text-xs text-[#FDE68A] leading-relaxed">{caution}</div></div>'

    about_block = ""
    if about:
        about_block = f'<div class="bunpro-about-content text-xs sm:text-sm text-neutral-200 leading-relaxed space-y-2 pt-1 border-t border-[#2C2C2C]">{about}</div>'

    return f'<div class="bunpro-card-details select-text text-left font-sans">{badges_html}{header}{struct_html}{caution_html}{about_block}</div>'
