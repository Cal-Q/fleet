"""
core/db_migrations/migrate_grammar_details.py — Migrate Bunpro Grammar Details & Sentences
Populates SQLite tables bunpro_grammar_details and bunpro_grammar_sentences
from JSON assets for instant querying and bonus disambiguation hints.
Strictly <= 200 lines invariant.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict

from core.db import open_dict_db
from core.db_migrations.schema_definitions import setup_tables


def _clean_jp(html: str) -> str:
    no_rt = re.sub(r"<r[tp]>[^<]*</r[tp]>", "", html)
    clean = re.sub(r"<[^>]+>", "", no_rt)
    return re.sub(r"[\s\u3000\.,!?。、！？\(\)（）]", "", clean)


def _clean_en(text: str) -> str:
    clean = re.sub(r"<[^>]+>", "", text).lower().strip()
    return re.sub(r"[\s\.,!?\(\)（）\"\']", "", clean)


def get_json_path(filename: str) -> Path:
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "japanese" / filename,
        Path("/opt/japan/japanese") / filename,
        Path("japanese") / filename,
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(f"Cannot find data file: {filename}")


def migrate_grammar_details(conn: sqlite3.Connection) -> int:
    path = get_json_path("bunpro_grammar_details.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries = []
    items = data.values() if isinstance(data, dict) else data
    for item in items:
        gid = item.get("id")
        if not gid:
            continue
        entries.append(
            (
                int(gid),
                item.get("title", ""),
                item.get("meaning", ""),
                item.get("level", ""),
                item.get("structure", ""),
                item.get("caution", ""),
                item.get("nuance", ""),
                item.get("register", ""),
            )
        )

    conn.executemany(
        """
        INSERT OR REPLACE INTO bunpro_grammar_details
        (id, title, meaning, level, structure, caution, nuance, register)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        entries,
    )
    return len(entries)


def migrate_grammar_sentences(conn: sqlite3.Connection) -> int:
    path = get_json_path("bunpro_grammar_sentences.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries = []
    for gid_str, gp in data.items():
        try:
            gid = int(gid_str)
        except ValueError:
            continue
        for s in gp.get("sentences", []):
            jp = s.get("clean_jp", s.get("japanese", ""))
            en = s.get("clean_en", s.get("english", ""))
            audio = s.get("audio_url", "")
            if not jp:
                continue
            entries.append((gid, jp, en, _clean_jp(jp), _clean_en(en), audio))

    conn.executemany(
        """
        INSERT INTO bunpro_grammar_sentences
        (grammar_id, japanese, english, clean_jp, clean_en, audio_url)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        entries,
    )
    return len(entries)


def run_migration() -> None:
    conn = open_dict_db(read_only=False)
    setup_tables(conn)
    conn.execute("DELETE FROM bunpro_grammar_sentences")
    d_count = migrate_grammar_details(conn)
    s_count = migrate_grammar_sentences(conn)
    conn.commit()
    conn.close()
    print(f"✅ Migrated {d_count} grammar details and {s_count} sentences to SQLite.")


if __name__ == "__main__":
    run_migration()
