"""Port of DictionaryExplorer.cs: provides dictionary access and fuzzy search."""

from __future__ import annotations

import os
import sqlite3

from . import jmdict_index
from .anki_deck_manager import AnkiDeckManager
from .dictionary_matcher import JMdictSearchResult, try_search_grouped
from .jmdict_models import CleanJMdictEntry, FuriganaSegment
from .local_files_manager import LocalFilesManager


class DictionaryExplorer:
    def __init__(self, local_files: LocalFilesManager):
        self._local_files = local_files
        self._conn: sqlite3.Connection | None = None
        self._ids_by_reading: dict[str, list[int]] = {}
        self._entry_by_id: dict[int, CleanJMdictEntry] = {}

    def initialize(self) -> None:
        jmdict_path = self._local_files.get_jmdict_file_path()
        jmenumdict_path = self._local_files.get_jmenumdict_file_path()
        furigana_path = self._local_files.get_furigana_file_path()

        db_path = jmdict_index.default_db_path(jmdict_path)
        if not os.path.isfile(db_path):
            from .jmdict_indexer import build_index
            build_index(db_path, jmdict_path, jmenumdict_path, furigana_path)

        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA mmap_size=536870912")

    def get_furigana(self, kanji_compound: str, full_reading: str) -> list[FuriganaSegment] | None:
        return jmdict_index.get_furigana(self._conn, kanji_compound, full_reading)

    def get_kodansha_kanji(self) -> list[tuple[int, str, str]]:
        if self._conn is None:
            raise RuntimeError("DictionaryExplorer.initialize() must be called first.")
        return self._conn.execute("SELECT id, kanji, keyword FROM kodansha_kanji ORDER BY id").fetchall()

    def get_source_english_to_kana(self) -> list[tuple[str, str]]:
        if self._conn is None:
            raise RuntimeError("DictionaryExplorer.initialize() must be called first.")
        return self._conn.execute("SELECT english, kana FROM source_english_to_kana ORDER BY id ASC").fetchall()

    def get_source_kanji_images(self) -> list[tuple[str, int, str]]:
        if self._conn is None:
            raise RuntimeError("DictionaryExplorer.initialize() must be called first.")
        return self._conn.execute("SELECT kanji, number, image FROM source_kanji_images ORDER BY id ASC").fetchall()

    def get_allowed_kanji(self) -> dict[str, int]:
        if self._conn is None:
            raise RuntimeError("DictionaryExplorer.initialize() must be called first.")
        cursor = self._conn.execute("SELECT kanji, number FROM source_kanji_images")
        return {row[0].strip()[0]: int(row[1]) for row in cursor.fetchall()}

    def prefetch(self, readings: set[str]) -> None:
        pending = {r for r in readings if r not in self._ids_by_reading}
        for _ in range(4):
            if not pending:
                break
            id_map = jmdict_index.get_entry_ids_by_readings(self._conn, pending)
            self._ids_by_reading.update(id_map)

            new_entry_ids = {eid for ids in id_map.values() for eid in ids if eid not in self._entry_by_id}
            hydrated = jmdict_index.hydrate_entries(self._conn, new_entry_ids)
            self._entry_by_id.update(hydrated)

            next_pending: set[str] = set()
            for entry in hydrated.values():
                for sense in entry.senses:
                    for xref in sense.parsed_cross_references:
                        for r in xref.readings:
                            if r not in self._ids_by_reading and r not in pending:
                                next_pending.add(r)
            pending = next_pending

    def get_entries(self, reading: str) -> list[CleanJMdictEntry]:
        ids = self._ids_by_reading.get(reading)
        if ids is None:
            ids = jmdict_index.get_entry_ids_by_reading(self._conn, reading)
            self._ids_by_reading[reading] = ids

        entries = []
        for entry_id in ids:
            entry = self._entry_by_id.get(entry_id)
            if entry is None:
                entry = jmdict_index.hydrate_entry(self._conn, entry_id)
                self._entry_by_id[entry_id] = entry
            entries.append(entry)
        return entries

    def try_search_grouped(
        self, deck_manager: AnkiDeckManager, english: str, kana: str
    ) -> tuple[bool, list[JMdictSearchResult]]:
        return try_search_grouped(self, deck_manager, english, kana)
