"""
Bunpro Grammar Details Extractor.

Parses local raw HTML pages to extract rich grammar explanations (About),
structures, nuances, cautions, and study resources for all 979 grammar points.
Strictly <= 200 lines invariant.
"""

import glob
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("grammar_extractor")


def to_ruby(text: str) -> str:
    """Convert Japanese parenthesis notation 漢字（ふりがな） into <ruby> markup."""
    return re.sub(r"([一-龯々]+)（([ぁ-んァ-ヶー]+)）", r"<ruby>\1<rt>\2</rt></ruby>", text)


def resolve_writeup_body(body: str, sqs: Dict[int, Dict[str, Any]]) -> str:
    """Substitute question placeholders with rich example cards."""
    if not body:
        return ""

    def replace_sq(match: re.Match) -> str:
        sq_id = int(match.group(1))
        q = sqs.get(sq_id)
        if not q:
            return ""
        content = q.get("content", "")
        ans = q.get("kanji_answer") or q.get("answer") or ""
        filled = content.replace("____", f'<strong class="text-[#66BB6A]">{ans}</strong>')
        filled_ruby = to_ruby(filled)
        trans = q.get("translation", "")
        return (
            f'<div class="my-2 p-2.5 rounded-xl bg-[#1A1A1A] border border-[#2D2D2D] text-left">'
            f'  <div class="jp-font font-bold text-white text-sm leading-snug mb-1">{filled_ruby}</div>'
            f'  <div class="text-xs text-neutral-300 font-sans leading-relaxed">{trans}</div>'
            f'</div>'
        )

    # Replace <li data-study-question='...'> or similar elements
    resolved = re.sub(r'<li\s+data-study-question=[\'"](\d+)[\'"][^>]*>(?:</li>)?', replace_sq, body)
    resolved = re.sub(r'<ul\s+class=[\'"]writeup-examples--holder[\'"]>', '<div class="space-y-1 my-2">', resolved)
    resolved = resolved.replace("</ul>", "</div>")
    resolved = re.sub(r'<span\s+data-gp-id=[\'"]\d+[\'"]>', '<span class="text-[#42A5F5] font-semibold">', resolved)
    return resolved.strip()


def extract_single_html(filepath: Path) -> Dict[str, Any]:
    """Extract reviewable and included metadata from Bunpro Next.js payload."""
    with open(filepath, "r", encoding="utf-8") as f:
        html = f.read()

    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html)
    if not m:
        return {}

    data = json.loads(m.group(1))
    props = data.get("props", {}).get("pageProps", {})
    rev = props.get("reviewable", {})
    inc = props.get("included", {})

    gp_id = rev.get("id")
    if not gp_id:
        return {}

    sqs = {sq["id"]: sq for sq in inc.get("studyQuestions", [])}
    writeups = inc.get("writeups", [])
    raw_body = writeups[0].get("body", "") if writeups else ""
    about_html = resolve_writeup_body(raw_body, sqs)

    structure = rev.get("polite_structure") or rev.get("casual_structure") or ""
    structure = to_ruby(structure).replace("<strong>", '<strong class="text-[#66BB6A]">')

    offline_res = [
        {"source": r.get("source"), "location": r.get("location")}
        for r in inc.get("offlineResources", [])
    ]
    online_res = [
        {"site": r.get("site"), "description": r.get("description"), "link": r.get("link")}
        for r in inc.get("supplementalLinks", [])
    ]

    return {
        "id": gp_id,
        "title": rev.get("title", ""),
        "meaning": rev.get("meaning", ""),
        "level": rev.get("level", "").replace("JLPT", "N"),
        "part_of_speech": rev.get("part_of_speech_translation") or rev.get("part_of_speech", ""),
        "word_type": rev.get("word_type_translation") or rev.get("word_type", ""),
        "register": rev.get("register_translation") or rev.get("register", ""),
        "structure": structure,
        "caution": rev.get("caution", ""),
        "nuance": rev.get("nuance_translation") or rev.get("nuance", ""),
        "about_html": about_html,
        "offline_resources": offline_res,
        "supplemental_links": online_res,
    }


def main():
    raw_dir = Path("japanese/bunpro_raw_html")
    files = sorted(raw_dir.glob("*.html"))
    logger.info(f"Found {len(files)} raw HTML files in {raw_dir}")

    details = {}
    for f in files:
        item = extract_single_html(f)
        if item and "id" in item:
            details[str(item["id"])] = item

    out_file = Path("japanese/bunpro_grammar_details.json")
    with open(out_file, "w", encoding="utf-8") as out:
        json.dump(details, out, ensure_ascii=False, indent=2)

    logger.info(f"Successfully extracted {len(details)} grammar details to {out_file}")


if __name__ == "__main__":
    main()
