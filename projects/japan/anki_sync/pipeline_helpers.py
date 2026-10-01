"""Helper dataclasses and ruby/furigana generators for deck update pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, TypeVar

from .anki_deck_manager import AnkiDeckManager

T = TypeVar("T")
K = TypeVar("K")


@dataclass(slots=True)
class MixedKanji:
    kanji: str
    kana: str
    english: str


def distinct(iterable: Iterable[T]) -> list[T]:
    """LINQ .Distinct() over a list: keeps first-occurrence order."""
    seen = set()
    result = []
    for item in iterable:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def group_by(items: list[T], key_func: Callable[[T], K]) -> list[tuple[K, list[T]]]:
    """LINQ .GroupBy() over a list: keeps first-occurrence group and item order."""
    groups: dict[K, list[T]] = {}
    for item in items:
        groups.setdefault(key_func(item), []).append(item)
    return list(groups.items())


def dict_add(d: dict, key, value) -> None:
    """Mirrors C#'s Dictionary<K,V>.Add: raises on duplicate key."""
    if key in d:
        raise KeyError(f"Duplicate key: {key!r}")
    d[key] = value


def generate_partial_kanji_cached(
    deck_manager: AnkiDeckManager,
    kanji_compound: str,
    full_reading: str,
    studied_kanji: set[str],
    cached_segments: list[dict[str, str]] | None = None,
) -> str:
    """Renders ruby tags for unstudied kanji using pre-cached furigana segments in RAM."""
    has_kanji = any(deck_manager.is_allowed_kanji_character(c) for c in kanji_compound)
    if not has_kanji:
        return kanji_compound

    if not cached_segments:
        for item in kanji_compound:
            if deck_manager.is_allowed_non_kanji_character(item):
                continue
            if deck_manager.is_allowed_kanji_character(item) and item not in studied_kanji:
                return f"<ruby>{kanji_compound}<rt>{full_reading}</rt></ruby>"
        return kanji_compound

    parts = []
    for seg in cached_segments:
        ruby = seg.ruby if hasattr(seg, "ruby") else seg.get("ruby", "")
        rt = seg.rt if hasattr(seg, "rt") else seg.get("rt", "")
        if not rt:
            parts.append(ruby)
        else:
            all_studied = all(c in studied_kanji for c in ruby)
            if all_studied:
                parts.append(ruby)
            else:
                parts.append(f"<ruby>{ruby}<rt>{rt}</rt></ruby>")
    return "".join(parts)


def resolve_all_single_kanji_meanings(conn, kanji_chars: set[str]) -> dict[str, str]:
    """Batch-resolves JMdict dictionary definitions for single-kanji words."""
    if not kanji_chars:
        return {}
    from . import jmdict_index

    placeholders = ",".join("?" for _ in kanji_chars)
    cur = conn.execute(
        f"SELECT DISTINCT r.reading, e.id FROM reading_elements r JOIN entries e ON e.id = r.entry_id "
        f"WHERE r.reading IN ({placeholders}) AND e.is_name_entry = 0 ORDER BY r.ord ASC",
        list(kanji_chars),
    )
    kanji_to_eids: dict[str, list[int]] = {}
    all_eids: set[int] = set()
    for reading, eid in cur.fetchall():
        kanji_to_eids.setdefault(reading, []).append(eid)
        all_eids.add(eid)
    if not all_eids:
        return {}

    entries_map = jmdict_index.hydrate_entries(conn, all_eids)
    results: dict[str, str] = {}
    pos_map = {"transitive verb": " [Vt]", "intransitive verb": " [Vi]", "noun or participle which takes the aux. verb suru": " [Vs]"}
    for k, eids in kanji_to_eids.items():
        for eid in eids:
            entry = entries_map.get(eid)
            if not entry:
                continue
            kana_readings = [r.reading for r in entry.reading_elements if not any("\u4e00" <= c <= "\u9faf" for c in r.reading)]
            if not kana_readings:
                continue
            r_blocks = []
            for kr in kana_readings:
                s_list = []
                for s in entry.senses:
                    if s.stagr and kr not in s.stagr:
                        continue
                    glosses = [g.text for g in s.glosses if g.text]
                    if not glosses:
                        continue
                    eng = ", ".join(glosses) + "".join(pos_map.get(p, "") for p in s.part_of_speech)
                    s_list.append(eng)
                if s_list:
                    r_blocks.append(f"{kr}<br>" + "<br>".join(f"- {txt}" for txt in s_list))
            if r_blocks:
                results[k] = "<br><br>".join(r_blocks)
                break
    return results


DISALLOWED_MISC_TAGS = {"archaic", "obsolete term", "rare term", "outdated term"}
DISALLOWED_INFO_TAGS = {
    "word containing irregular kanji usage",
    "word containing out-dated kanji or kanji usage",
    "rarely used kanji form",
    "search-only kanji form",
    "irregular okurigana usage",
}


def compute_priority_score(pri_tags: list[str]) -> int:
    """Calculates numerical score for JMdict frequency/priority tags."""
    if not pri_tags:
        return 0
    score = 0
    for tag in pri_tags:
        if tag in ("ichi1", "news1", "spec1"):
            score += 1000
        elif tag in ("ichi2", "news2", "spec2", "gai1"):
            score += 500
        elif tag.startswith("nf"):
            try:
                score += max(0, 100 - int(tag[2:])) * 10
            except ValueError:
                score += 50
        else:
            score += 10
    return score


def is_entry_archaic(entry) -> bool:
    """Returns True if all senses of an entry are archaic or obsolete."""
    if not entry.senses:
        return False
    return all(any(tag in DISALLOWED_MISC_TAGS for tag in s.misc) for s in entry.senses)


def filter_valid_reading_elements(entry, deck_manager) -> list[str]:
    """Filters reading elements, selecting only the highest-priority canonical forms."""
    candidates = []
    for re_el in entry.reading_elements:
        kw = re_el.reading
        if any(not deck_manager.is_allowed_character(c) for c in kw):
            continue
        if any(tag in DISALLOWED_INFO_TAGS for tag in re_el.info):
            continue
        if any(deck_manager.is_allowed_kanji_character(c) for c in kw):
            candidates.append(re_el)

    if not candidates:
        return []

    scored = [(c, compute_priority_score(c.priority)) for c in candidates]
    max_score = max(s for _, s in scored)
    if max_score > 0:
        return [c.reading for c, s in scored if s == max_score]
    return [candidates[0].reading]

