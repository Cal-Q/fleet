"""SQLite-backed index reader over JMdict + JMnedict + Furigana."""

from __future__ import annotations

import json
import os
import sqlite3

from .jmdict_indexer import build_index
from .jmdict_models import CleanJMdictEntry, FuriganaSegment, Gloss, ReadingElement, Sense


def default_db_path(jmdict_path: str) -> str:
    return os.path.join(os.path.dirname(jmdict_path), "dict_index.sqlite3")


def _mtime_matches(stored_val: str | None, current_val: str) -> bool:
    if not stored_val or not current_val:
        return False
    try:
        return int(float(stored_val)) == int(float(current_val))
    except (ValueError, TypeError):
        return stored_val == current_val


def is_index_valid(db_path: str, jmdict_path: str, jmenumdict_path: str, furigana_path: str) -> bool:
    if not os.path.isfile(db_path):
        return False
    try:
        conn = sqlite3.connect(db_path)
        try:
            stored = dict(conn.execute("SELECT key, value FROM meta"))
        finally:
            conn.close()
    except sqlite3.Error:
        return False

    def mt(p: str) -> str:
        return str(int(os.path.getmtime(p))) if os.path.isfile(p) else ""

    return (
        _mtime_matches(stored.get("jmdict_mtime"), mt(jmdict_path))
        and _mtime_matches(stored.get("jmenumdict_mtime"), mt(jmenumdict_path))
        and _mtime_matches(stored.get("furigana_mtime"), mt(furigana_path))
    )


def get_entry_ids_by_reading(conn: sqlite3.Connection, reading: str) -> list[int]:
    return [r[0] for r in conn.execute("SELECT DISTINCT entry_id FROM reading_elements WHERE reading = ?", (reading,))]


def _chunks(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def get_entry_ids_by_readings(conn: sqlite3.Connection, readings: set[str]) -> dict[str, list[int]]:
    readings_list = list(readings)
    result: dict[str, list[int]] = {r: [] for r in readings_list}
    for chunk in _chunks(readings_list, 500):
        placeholders = ",".join("?" for _ in chunk)
        for entry_id, reading in conn.execute(
            f"SELECT DISTINCT entry_id, reading FROM reading_elements WHERE reading IN ({placeholders})", chunk
        ):
            result[reading].append(entry_id)
    return result


def hydrate_entries(conn: sqlite3.Connection, entry_ids: set[int]) -> dict[int, CleanJMdictEntry]:
    ids_list = list(entry_ids)
    if not ids_list:
        return {}

    is_name_entry_by_id: dict[int, int] = {}
    for chunk in _chunks(ids_list, 500):
        placeholders = ",".join("?" for _ in chunk)
        for eid, is_name in conn.execute(f"SELECT id, is_name_entry FROM entries WHERE id IN ({placeholders})", chunk):
            is_name_entry_by_id[eid] = is_name

    reading_elements_by_entry: dict[int, list[ReadingElement]] = {eid: [] for eid in ids_list}
    for chunk in _chunks(ids_list, 500):
        placeholders = ",".join("?" for _ in chunk)
        for eid, reading, info, priority in conn.execute(
            f"SELECT entry_id, reading, info, priority FROM reading_elements WHERE entry_id IN ({placeholders}) ORDER BY entry_id, ord", chunk
        ):
            reading_elements_by_entry[eid].append(ReadingElement(reading=reading, info=json.loads(info), priority=json.loads(priority)))

    sense_rows_by_entry: dict[int, list[tuple]] = {eid: [] for eid in ids_list}
    sense_id_to_entry: dict[int, int] = {}
    for chunk in _chunks(ids_list, 500):
        placeholders = ",".join("?" for _ in chunk)
        for row in conn.execute(
            f"SELECT entry_id, id, stagk, stagr, part_of_speech, cross_references, antonyms, field_, misc, sense_info, dialects FROM senses WHERE entry_id IN ({placeholders}) ORDER BY entry_id, ord", chunk
        ):
            sense_rows_by_entry[row[0]].append(row[1:])
            sense_id_to_entry[row[1]] = row[0]

    all_sense_ids = list(sense_id_to_entry.keys())
    glosses_by_sense: dict[int, list[Gloss]] = {sid: [] for sid in all_sense_ids}
    for chunk in _chunks(all_sense_ids, 500):
        placeholders = ",".join("?" for _ in chunk)
        for sense_id, text, language in conn.execute(
            f"SELECT sense_id, text, language FROM glosses WHERE sense_id IN ({placeholders}) ORDER BY sense_id, ord", chunk
        ):
            glosses_by_sense[sense_id].append(Gloss(text=text, language=language))

    result: dict[int, CleanJMdictEntry] = {}
    for eid in ids_list:
        reading_elements = reading_elements_by_entry[eid]
        readings = {re_.reading for re_ in reading_elements}
        senses = [
            Sense(
                stagk=json.loads(stagk),
                stagr=json.loads(stagr),
                part_of_speech=json.loads(pos),
                cross_references=json.loads(xrefs),
                antonyms=json.loads(ant),
                field_=json.loads(field_),
                misc=json.loads(misc),
                sense_info=json.loads(sinfo),
                dialects=json.loads(dial),
                glosses=glosses_by_sense[sense_id],
            )
            for sense_id, stagk, stagr, pos, xrefs, ant, field_, misc, sinfo, dial in sense_rows_by_entry[eid]
        ]
        result[eid] = CleanJMdictEntry(
            id=eid,
            senses=senses,
            reading_elements=reading_elements,
            readings=readings,
            is_name_entry=bool(is_name_entry_by_id.get(eid, 0)),
        )

    return result


def hydrate_entry(conn: sqlite3.Connection, entry_id: int) -> CleanJMdictEntry:
    is_name_entry = conn.execute("SELECT is_name_entry FROM entries WHERE id = ?", (entry_id,)).fetchone()[0]
    reading_elements = [
        ReadingElement(reading=reading, info=json.loads(info), priority=json.loads(priority))
        for reading, info, priority in conn.execute(
            "SELECT reading, info, priority FROM reading_elements WHERE entry_id = ? ORDER BY ord", (entry_id,)
        )
    ]
    readings = {re_.reading for re_ in reading_elements}

    sense_rows = conn.execute(
        "SELECT id, stagk, stagr, part_of_speech, cross_references, antonyms, field_, misc, sense_info, dialects FROM senses WHERE entry_id = ? ORDER BY ord",
        (entry_id,),
    ).fetchall()

    sense_ids = [row[0] for row in sense_rows]
    glosses_by_sense: dict[int, list[Gloss]] = {sid: [] for sid in sense_ids}
    if sense_ids:
        placeholders = ",".join("?" for _ in sense_ids)
        for sense_id, text, language in conn.execute(
            f"SELECT sense_id, text, language FROM glosses WHERE sense_id IN ({placeholders}) ORDER BY sense_id, ord", sense_ids
        ):
            glosses_by_sense[sense_id].append(Gloss(text=text, language=language))

    senses = [
        Sense(
            stagk=json.loads(stagk),
            stagr=json.loads(stagr),
            part_of_speech=json.loads(pos),
            cross_references=json.loads(xrefs),
            antonyms=json.loads(ant),
            field_=json.loads(field_),
            misc=json.loads(misc),
            sense_info=json.loads(sinfo),
            dialects=json.loads(dial),
            glosses=glosses_by_sense[sense_id],
        )
        for sense_id, stagk, stagr, pos, xrefs, ant, field_, misc, sinfo, dial in sense_rows
    ]

    return CleanJMdictEntry(id=entry_id, senses=senses, reading_elements=reading_elements, readings=readings, is_name_entry=bool(is_name_entry))


def get_furigana(conn: sqlite3.Connection, text: str, reading: str) -> list[FuriganaSegment] | None:
    row = conn.execute("SELECT segments FROM furigana WHERE text = ? AND reading = ? LIMIT 1", (text, reading)).fetchone()
    if row is None:
        return None
    return [FuriganaSegment(ruby=ruby, rt=rt) for ruby, rt in json.loads(row[0])]
