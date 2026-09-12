"""Precompiled incremental cache for vocabulary dictionary lookups.

Eliminates full JMdict XML rescans by caching resolved linguistic structures.
"""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .anki_deck_manager import AnkiDeckManager
    from .dictionary_explorer import DictionaryExplorer


def ensure_cache_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS source_vocab_resolved (
            english TEXT,
            kana TEXT,
            data_json TEXT,
            PRIMARY KEY (english, kana)
        )
        """
    )


def load_all_resolved(conn: sqlite3.Connection) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """Loads all precompiled vocab entries into memory in a single query (~5ms)."""
    ensure_cache_table(conn)
    cursor = conn.execute("SELECT english, kana, data_json FROM source_vocab_resolved")
    result: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for eng, kana, raw_json in cursor.fetchall():
        try:
            result[(eng, kana)] = json.loads(raw_json)
        except (ValueError, TypeError):
            pass
    return result


def save_resolved_batch(
    conn: sqlite3.Connection, batch: list[tuple[str, str, str]]
) -> None:
    """Saves a batch of resolved entries into SQLite."""
    if not batch:
        return
    ensure_cache_table(conn)
    conn.executemany(
        "INSERT OR REPLACE INTO source_vocab_resolved (english, kana, data_json) VALUES (?, ?, ?)",
        batch,
    )
    conn.commit()


def serialize_search_results(
    results: list[Any], dict_explorer: DictionaryExplorer
) -> list[dict[str, Any]]:
    """Converts raw JMdictSearchResult objects into lightweight serializable dicts."""
    serialized = []
    for item in results:
        kanji_words = [el.reading for el in item.entry.reading_elements]
        senses_formatted = []
        for sense in item.entry.senses:
            eng = item.research_english
            for pos in sense.part_of_speech:
                if pos == "transitive verb":
                    eng += " [Vt]"
                elif pos == "intransitive verb":
                    eng += " [Vi]"
                elif pos == "noun or participle which takes the aux. verb suru":
                    eng += " [Vs]"
            for bonus in sense.get_bonus_info():
                if bonus == "word usually written using kana alone":
                    eng += " [Ko]"
                else:
                    eng += f" ({bonus})"
            senses_formatted.append(eng)

        # Pre-cache furigana segments for each kanji word
        furigana_data: dict[str, list[dict[str, str]]] = {}
        for kw in kanji_words:
            segs = dict_explorer.get_furigana(kw, item.research_kana)
            if segs:
                furigana_data[kw] = [{"ruby": s.ruby, "rt": s.rt} for s in segs]

        serialized.append(
            {
                "kanji_words": kanji_words,
                "senses": senses_formatted,
                "furigana": furigana_data,
                "research_english": item.research_english,
                "research_kana": item.research_kana,
            }
        )
    return serialized


def get_or_resolve_vocab(
    conn_or_path: sqlite3.Connection | str,
    deck_manager: AnkiDeckManager,
    dict_explorer: DictionaryExplorer,
    source_vocab: list[tuple[str, str]],
) -> list[dict[str, Any]]:
    """Returns resolved entries for all source vocab, incrementally resolving only new ones."""
    if isinstance(conn_or_path, str):
        conn = sqlite3.connect(conn_or_path)
        should_close = True
    else:
        conn = conn_or_path
        should_close = False
    try:
        cached = load_all_resolved(conn)
        missing_pairs = []

        for english, back in source_vocab:
            for kana in (k for k in back.split("<br>") if k):
                if (english, kana) not in cached:
                    missing_pairs.append((english, kana))

        if missing_pairs:
            missing_kana = {k for _, k in missing_pairs}
            dict_explorer.prefetch(missing_kana)

            new_batch = []
            for eng, kana in missing_pairs:
                found, top_results = dict_explorer.try_search_grouped(deck_manager, eng, kana)
                if found:
                    data = serialize_search_results(top_results, dict_explorer)
                    cached[(eng, kana)] = data
                    new_batch.append((eng, kana, json.dumps(data, ensure_ascii=False)))
                else:
                    cached[(eng, kana)] = []
                    new_batch.append((eng, kana, "[]"))

            save_resolved_batch(conn, new_batch)

        all_entries: list[dict[str, Any]] = []
        for english, back in source_vocab:
            for kana in (k for k in back.split("<br>") if k):
                entries = cached.get((english, kana), [])
                all_entries.extend(entries)

        return all_entries
    finally:
        if should_close:
            conn.close()
