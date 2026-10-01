#!/usr/bin/env python3
"""
core/anki_meanings_parser.py — Upstream Anki Meanings & Multi-Reading Parser
Parses, scores, and ranks multi-reading blocks and dictionary senses.
Strictly <= 200 lines invariant.
"""
import re
from typing import Any, Dict, List


def extract_ruby_reading(ruby_raw: str) -> str:
    """Extracts clean reading string from ruby rt tags or raw text."""
    if not ruby_raw:
        return ""
    rt_matches = re.findall(r"<rt>(.*?)</rt>", ruby_raw, flags=re.IGNORECASE)
    if rt_matches:
        return "".join(re.sub(r"<[^>]+>", "", m).strip() for m in rt_matches)
    return re.sub(r"<[^>]+>", "", ruby_raw).strip()


def parse_card_meanings(meaning_raw: str, primary_hint: str = "") -> Dict[str, Any]:
    """
    Extracts all reading blocks and senses, ranking primary vocabulary definitions
    above rare variants or surname entries.
    """
    if not meaning_raw:
        return {"primary_reading": primary_hint, "readings": [], "primary_meaning": ""}

    raw = re.sub(r"\[sound:[^\]]+\]", "", meaning_raw)
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"<br\s*/?>\s*<br\s*/?>|\n\n", raw)
    readings: List[Dict[str, Any]] = []

    for b in blocks:
        b = b.strip()
        if not b:
            continue
        parts = [p.strip() for p in re.split(r"<br\s*/?>|\n", b) if p.strip()]
        if not parts:
            continue

        if not parts[0].startswith("-") and not parts[0].startswith("•") and not parts[0].startswith("("):
            kana = re.sub(r"<[^>]+>", "", parts[0]).strip()
            sense_lines = parts[1:]
        else:
            kana = primary_hint or "標準"
            sense_lines = parts

        scored_senses = []
        name_count = 0
        for s in sense_lines:
            clean_s = re.sub(r"^[-•\s]+", "", s).strip()
            clean_s = re.sub(r"\s*\[[^\]]*[\u4e00-\u9faf\u3040-\u30ff々〆ヵヶ\u3000-\u303f\uff00-\uffef][^\]]*\]", "", clean_s).strip()
            if not clean_s:
                continue
            lower_s = clean_s.lower()
            is_name = any(k in lower_s for k in [
                "family or surname", "given name", "place name",
                "unclassified name", "full name", "female given name", "male given name"
            ])
            is_rare = any(k in lower_s for k in ["archaic", "obsolete", "rare term", "obscure"])
            if is_name:
                score = 1
                name_count += 1
            elif is_rare:
                score = 10
            elif "abbreviation" in lower_s:
                score = 60
            else:
                score = 100
            scored_senses.append((score, clean_s))

        scored_senses.sort(key=lambda x: x[0], reverse=True)
        senses = [x[1] for x in scored_senses]
        if not senses and not kana:
            continue

        is_primary = False
        if primary_hint and (kana == primary_hint or primary_hint in kana or kana in primary_hint):
            is_primary = True

        has_real_words = any(x[0] >= 50 for x in scored_senses)
        r_score = 0
        if is_primary:
            r_score += 2000
        if has_real_words:
            r_score += 500
        r_score += len(senses) * 10 - name_count * 30

        top_snippet = senses[0] if senses else ""
        if len(top_snippet) > 28:
            top_snippet = top_snippet[:28] + "…"

        readings.append({
            "kana": kana,
            "senses": senses,
            "score": r_score,
            "is_primary": is_primary,
            "top_snippet": top_snippet
        })

    readings.sort(key=lambda x: x["score"], reverse=True)
    top_reading = readings[0]["kana"] if readings else primary_hint
    top_senses = readings[0]["senses"] if readings else []
    top_meaning_html = "<br>".join(f"• {s}" for s in top_senses) if top_senses else meaning_raw

    return {
        "primary_reading": top_reading,
        "readings": readings,
        "primary_meaning": top_meaning_html
    }
