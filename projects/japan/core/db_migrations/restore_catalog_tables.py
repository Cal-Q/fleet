"""
core/db_migrations/restore_catalog_tables.py — Reconciles study targets from Anki.
Restores kanji_catalog, bunpro_grammar_points, and jlpt_vocab into dict_index.
Strictly <= 200 lines invariant.
"""

from __future__ import annotations

import os
import re
import sqlite3
import sys
import time

DICT_DB = "/opt/japan/data/dict_index.sqlite3"
BAK_DB = "/opt/japan/data/dict_index.sqlite3.bak_20260924_2046"
ANKI_DB = "/opt/japan/.local/share/Anki2/User 1/collection.anki2"


def restore_and_reconcile() -> None:
    if not os.path.exists(BAK_DB):
        print(f"Backup DB not found: {BAK_DB}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(DICT_DB):
        print(f"Target DB not found: {DICT_DB}", file=sys.stderr)
        sys.exit(1)

    src = sqlite3.connect(BAK_DB)
    dst = sqlite3.connect(DICT_DB)
    dst.execute("PRAGMA foreign_keys = OFF")

    # 1. Restore kanji_catalog
    print("[1/5] Restoring kanji_catalog...")
    dst.execute("DELETE FROM kanji_catalog")
    k_rows = src.execute(
        """
        SELECT id, kanji, keyword, jlpt_level, on_reading, kun_reading,
               main_on_reading, diagram, image, in_anki, is_study_target,
               status, reps, last_studied_at
        FROM kanji_catalog
        """
    ).fetchall()
    dst.executemany(
        """
        INSERT INTO kanji_catalog (
            id, kanji, keyword, jlpt_level, on_reading, kun_reading,
            main_on_reading, diagram, image, in_anki, is_study_target,
            status, reps, last_studied_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        k_rows,
    )
    print(f"  Inserted {len(k_rows)} kanji rows.")

    # 2. Restore bunpro_grammar_points
    print("[2/5] Restoring bunpro_grammar_points...")
    dst.execute("DELETE FROM bunpro_grammar_points")
    g_rows = src.execute(
        """
        SELECT id, level, title, meaning, category, url, in_anki,
               is_study_target, status, matched_sentences, total_sentences,
               studied_at
        FROM bunpro_grammar_points
        """
    ).fetchall()
    dst.executemany(
        """
        INSERT INTO bunpro_grammar_points (
            id, level, title, meaning, category, url, in_anki,
            is_study_target, status, matched_sentences, total_sentences,
            studied_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        g_rows,
    )
    print(f"  Inserted {len(g_rows)} grammar rows.")

    # 3. Restore jlpt_vocab
    print("[3/5] Restoring jlpt_vocab...")
    dst.execute("DELETE FROM jlpt_vocab")
    v_rows = src.execute(
        """
        SELECT id, vocab_id, level, word, reading, raw, in_anki,
               is_study_target, status, reps
        FROM jlpt_vocab
        """
    ).fetchall()
    dst.executemany(
        """
        INSERT INTO jlpt_vocab (
            id, vocab_id, level, word, reading, raw, in_anki,
            is_study_target, status, reps
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        v_rows,
    )
    print(f"  Inserted {len(v_rows)} vocab rows.")
    dst.commit()

    # 4. Reconcile against live Anki collection if present
    if os.path.exists(ANKI_DB):
        print("[4/5] Reconciling against live Anki collection...")
        aconn = sqlite3.connect(ANKI_DB)
        now_ts = int(time.time() * 1000)

        # 4a. Kanji reconciliation
        k_query = """
            SELECT n.flds, c.reps, c.mod
            FROM notes n
            JOIN cards c ON c.nid = n.id
            WHERE c.did IN (1757158925901, 1758314901201)
        """
        for flds, reps, mod in aconn.execute(k_query):
            k = flds.split("\x1f")[0].strip()
            if len(k) == 1:
                status = "studied" if reps > 0 else "studying"
                dst.execute(
                    """
                    UPDATE kanji_catalog
                    SET in_anki = 1, status = ?, reps = ?, last_studied_at = ?
                    WHERE kanji = ?
                    """,
                    (status, reps, mod, k),
                )

        # 4b. Grammar points reconciliation via Anki sentence matching
        anki_sents = set()
        s_query = """
            SELECT n.flds FROM notes n
            JOIN cards c ON c.nid = n.id
            WHERE c.did = 1770845308673
        """
        for (flds,) in aconn.execute(s_query):
            en = flds.split("\x1f")[0].strip().lower()
            anki_sents.add(en)

        cur_act = dst.cursor()
        cur_act.execute(
            "SELECT grammar_id, clean_en FROM bunpro_grammar_sentences"
        )
        gids_in_anki = set()
        for gid, c_en in cur_act.fetchall():
            if c_en and c_en.strip().lower() in anki_sents:
                gids_in_anki.add(gid)

        for gid in gids_in_anki:
            dst.execute(
                """
                UPDATE bunpro_grammar_points
                SET in_anki = 1, status = 'studied', studied_at = ?
                WHERE id = ?
                """,
                (now_ts, gid),
            )
        print(f"  Reconciled {len(gids_in_anki)} grammar points with Anki.")

        # 4c. Vocab reconciliation
        v_query = """
            SELECT n.flds, c.reps FROM notes n
            JOIN cards c ON c.nid = n.id
            WHERE c.did = 1759999324396
        """
        for flds, reps in aconn.execute(v_query):
            w_raw = flds.split("\x1f")[0]
            clean_w = re.sub(r"<rt>.*?</rt>", "", w_raw)
            clean_w = clean_w.replace("<ruby>", "").replace("</ruby>", "").strip()
            if clean_w:
                status = "studied" if reps > 0 else "studying"
                dst.execute(
                    """
                    UPDATE jlpt_vocab
                    SET in_anki = 1, status = ?, reps = ?
                    WHERE word = ?
                    """,
                    (status, reps, clean_w),
                )
        aconn.close()
        dst.commit()

    # 5. Final counts
    print("[5/5] Verification summary:")
    for t in ["kanji_catalog", "bunpro_grammar_points", "jlpt_vocab"]:
        total = dst.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        in_anki = dst.execute(
            f"SELECT count(*) FROM {t} WHERE in_anki = 1"
        ).fetchone()[0]
        print(f"  {t}: total={total}, in_anki={in_anki}")

    dst.close()
    src.close()
    print("Restore and reconciliation completed successfully.")


if __name__ == "__main__":
    restore_and_reconcile()
