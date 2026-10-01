"""
core/db_migrations/migrate_grammar_coverage.py — Migrate Bunpro Grammar Vocab Coverage
Populates SQLite table bunpro_grammar_vocab_coverage from JSON assets for fast gating queries.
Strictly <= 200 lines invariant.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import sys

_PROJ_DIR = str(Path(__file__).resolve().parent.parent.parent)
if _PROJ_DIR not in sys.path:
    sys.path.insert(0, _PROJ_DIR)

from core.db import open_dict_db
from core.db_migrations.schema_definitions import setup_tables


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


def migrate_grammar_vocab_coverage(conn: sqlite3.Connection) -> int:
    path = get_json_path("bunpro_grammar_vocab_coverage.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cov = data.get("grammar_coverage", {})
    entries = []
    for gid_str, g_data in cov.items():
        try:
            gid = int(gid_str)
        except ValueError:
            continue
        for v in g_data.get("vocab", []):
            vid = v.get("id")
            if vid is None:
                continue
            entries.append(
                (
                    gid,
                    int(vid),
                    v.get("title", ""),
                    v.get("furigana", ""),
                    v.get("meaning", ""),
                    v.get("level", ""),
                )
            )

    conn.executemany(
        """
        INSERT OR REPLACE INTO bunpro_grammar_vocab_coverage
        (grammar_id, vocab_id, title, furigana, meaning, level)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        entries,
    )
    return len(entries)


def run_migration() -> None:
    conn = open_dict_db(read_only=False)
    setup_tables(conn)
    count = migrate_grammar_vocab_coverage(conn)
    conn.commit()
    conn.close()
    print(f"✅ Migrated {count} grammar vocab coverage entries to SQLite.")


if __name__ == "__main__":
    run_migration()
