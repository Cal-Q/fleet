"""Schema definition and builder for dict_index.sqlite3."""

from __future__ import annotations

import itertools
import json
import os
import sqlite3

from .jmdict_models import CleanJMdictEntry
from .jmdict_xml import iter_jmdict_entries, iter_jmnedict_entries

_SCHEMA = """
CREATE TABLE entries (
    id INTEGER PRIMARY KEY,
    is_name_entry INTEGER NOT NULL
);

CREATE TABLE reading_elements (
    entry_id INTEGER NOT NULL,
    ord INTEGER NOT NULL,
    reading TEXT NOT NULL,
    info TEXT NOT NULL,
    priority TEXT NOT NULL
);
CREATE INDEX ix_reading_elements_reading ON reading_elements(reading);
CREATE INDEX ix_reading_elements_entry ON reading_elements(entry_id, ord);

CREATE TABLE senses (
    id INTEGER PRIMARY KEY,
    entry_id INTEGER NOT NULL,
    ord INTEGER NOT NULL,
    stagk TEXT NOT NULL,
    stagr TEXT NOT NULL,
    part_of_speech TEXT NOT NULL,
    cross_references TEXT NOT NULL,
    antonyms TEXT NOT NULL,
    field_ TEXT NOT NULL,
    misc TEXT NOT NULL,
    sense_info TEXT NOT NULL,
    dialects TEXT NOT NULL
);
CREATE INDEX ix_senses_entry ON senses(entry_id);

CREATE TABLE glosses (
    sense_id INTEGER NOT NULL,
    ord INTEGER NOT NULL,
    text TEXT,
    language TEXT NOT NULL
);
CREATE INDEX ix_glosses_sense ON glosses(sense_id);

CREATE TABLE furigana (
    text TEXT NOT NULL,
    reading TEXT NOT NULL,
    segments TEXT NOT NULL
);
CREATE INDEX ix_furigana_text_reading ON furigana(text, reading);

CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _mtime(path: str) -> str:
    return str(int(os.path.getmtime(path))) if os.path.isfile(path) else ""


def build_index(db_path: str, jmdict_path: str, jmenumdict_path: str, furigana_path: str) -> None:
    tmp_path = db_path + ".building"
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    conn = sqlite3.connect(tmp_path)
    try:
        conn.execute("PRAGMA journal_mode=OFF")
        conn.execute("PRAGMA synchronous=OFF")
        conn.executescript(_SCHEMA)

        entry_id = 0
        for entry in itertools.chain(iter_jmnedict_entries(jmenumdict_path), iter_jmdict_entries(jmdict_path)):
            entry_id += 1
            _insert_entry(conn, entry_id, entry)

        if os.path.isfile(furigana_path):
            _insert_furigana(conn, furigana_path)

        conn.executemany(
            "INSERT INTO meta (key, value) VALUES (?, ?)",
            [
                ("jmdict_mtime", _mtime(jmdict_path)),
                ("jmenumdict_mtime", _mtime(jmenumdict_path)),
                ("furigana_mtime", _mtime(furigana_path)),
            ],
        )
        conn.commit()
    finally:
        conn.close()

    os.replace(tmp_path, db_path)


def _insert_entry(conn: sqlite3.Connection, entry_id: int, entry: CleanJMdictEntry) -> None:
    conn.execute("INSERT INTO entries (id, is_name_entry) VALUES (?, ?)", (entry_id, int(entry.is_name_entry)))

    conn.executemany(
        "INSERT INTO reading_elements (entry_id, ord, reading, info, priority) VALUES (?, ?, ?, ?, ?)",
        [
            (entry_id, ord_, re_.reading, json.dumps(re_.info), json.dumps(re_.priority))
            for ord_, re_ in enumerate(entry.reading_elements)
        ],
    )

    for ord_, sense in enumerate(entry.senses):
        cursor = conn.execute(
            """
            INSERT INTO senses
                (entry_id, ord, stagk, stagr, part_of_speech, cross_references, antonyms, field_, misc, sense_info, dialects)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry_id,
                ord_,
                json.dumps(sense.stagk),
                json.dumps(sense.stagr),
                json.dumps(sense.part_of_speech),
                json.dumps(sense.cross_references),
                json.dumps(sense.antonyms),
                json.dumps(sense.field_),
                json.dumps(sense.misc),
                json.dumps(sense.sense_info),
                json.dumps(sense.dialects),
            ),
        )
        sense_id = cursor.lastrowid

        conn.executemany(
            "INSERT INTO glosses (sense_id, ord, text, language) VALUES (?, ?, ?, ?)",
            [(sense_id, g_ord, gloss.text, gloss.language) for g_ord, gloss in enumerate(sense.glosses)],
        )


def _insert_furigana(conn: sqlite3.Connection, furigana_path: str) -> None:
    with open(furigana_path, "r", encoding="utf-8-sig") as f:
        raw = json.load(f)

    conn.executemany(
        "INSERT INTO furigana (text, reading, segments) VALUES (?, ?, ?)",
        (
            (
                item.get("text", ""),
                item.get("reading", ""),
                json.dumps([[seg.get("ruby", ""), seg.get("rt")] for seg in item.get("furigana", [])]),
            )
            for item in raw
        ),
    )
