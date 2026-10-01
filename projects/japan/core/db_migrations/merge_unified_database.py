"""
core/db_migrations/merge_unified_database.py — Restores unified dict_index.
Merges full JMdict dictionary (entries, reading_elements, senses, glosses)
with modern Bunpro and reconciled study catalog tables.
Strictly <= 200 lines invariant.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import time

DICT_PATH = "/opt/japan/data/dict_index.sqlite3"
BAK_PATH = "/opt/japan/data/dict_index.sqlite3.bak_20260924_2046"
TEMP_PATH = "/opt/japan/data/dict_index_unified.sqlite3"


def merge_database() -> None:
    if not os.path.exists(BAK_PATH):
        print(f"Error: master backup {BAK_PATH} not found", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(DICT_PATH):
        print(f"Error: current db {DICT_PATH} not found", file=sys.stderr)
        sys.exit(1)

    t0 = time.time()
    print("[1/5] Creating working copy from master JMdict backup...")
    shutil.copyfile(BAK_PATH, TEMP_PATH)
    print(f"  Working copy created in {round(time.time() - t0, 2)}s.")

    con = sqlite3.connect(TEMP_PATH)
    con.execute("PRAGMA synchronous = NORMAL")
    con.execute("PRAGMA journal_mode = WAL")
    con.execute(f"ATTACH '{DICT_PATH}' AS active_db")

    print("[2/5] Updating bunpro_grammar_details...")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS bunpro_grammar_details (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            meaning TEXT,
            level TEXT,
            structure TEXT,
            caution TEXT,
            nuance TEXT,
            register TEXT
        )
        """
    )
    con.execute("DELETE FROM bunpro_grammar_details")
    con.execute(
        """
        INSERT INTO bunpro_grammar_details
        SELECT * FROM active_db.bunpro_grammar_details
        """
    )

    print("[3/5] Updating bunpro_grammar_vocab_coverage...")
    con.execute("DROP TABLE IF EXISTS bunpro_grammar_vocab_coverage")
    cov_sql = active_db_sql = con.execute(
        """
        SELECT sql FROM active_db.sqlite_master
        WHERE name = 'bunpro_grammar_vocab_coverage'
        """
    ).fetchone()[0]
    con.execute(cov_sql)
    con.execute(
        """
        INSERT INTO bunpro_grammar_vocab_coverage
        SELECT * FROM active_db.bunpro_grammar_vocab_coverage
        """
    )
    con.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_coverage_grammar_id
        ON bunpro_grammar_vocab_coverage(grammar_id)
        """
    )

    print("[4/5] Syncing reconciled study catalog tables...")
    for tbl in ["kanji_catalog", "bunpro_grammar_points", "jlpt_vocab"]:
        con.execute(f"DELETE FROM {tbl}")
        con.execute(f"INSERT INTO {tbl} SELECT * FROM active_db.{tbl}")
        cnt = con.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0]
        in_a = con.execute(
            f"SELECT count(*) FROM {tbl} WHERE in_anki = 1"
        ).fetchone()[0]
        print(f"  {tbl}: total={cnt}, in_anki={in_a}")

    con.commit()
    con.close()

    print("[5/5] Replacing active dict_index.sqlite3 with unified database...")
    backup_slim = DICT_PATH + ".slim_before_unified_restore"
    if os.path.exists(DICT_PATH):
        shutil.move(DICT_PATH, backup_slim)
    shutil.move(TEMP_PATH, DICT_PATH)

    # Verification
    v_conn = sqlite3.connect(DICT_PATH)
    v_cur = v_conn.cursor()
    print("Verification checks on unified dict_index.sqlite3:")
    for check_tbl in [
        "entries",
        "reading_elements",
        "senses",
        "glosses",
        "furigana",
        "kanji_catalog",
        "bunpro_grammar_points",
        "jlpt_vocab",
        "bunpro_grammar_sentences",
        "bunpro_grammar_details",
        "bunpro_grammar_vocab_coverage",
    ]:
        c = v_cur.execute(f"SELECT count(*) FROM {check_tbl}").fetchone()[0]
        print(f"  ✓ {check_tbl}: {c} rows")
    v_conn.close()
    print(f"Unified database successfully restored in {round(time.time() - t0, 2)}s.")


if __name__ == "__main__":
    merge_database()
