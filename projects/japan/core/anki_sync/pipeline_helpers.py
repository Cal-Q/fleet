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
        ruby = seg.get("ruby", "")
        rt = seg.get("rt", "")
        if not rt:
            parts.append(ruby)
        else:
            all_studied = all(c in studied_kanji for c in ruby)
            if all_studied:
                parts.append(ruby)
            else:
                parts.append(f"<ruby>{ruby}<rt>{rt}</rt></ruby>")
    return "".join(parts)
