"""Migration script: bootstraps unified study target tables from Anki & JSONs."""

from __future__ import annotations

import json
import os
import sqlite3
import time

from .schema_definitions import setup_tables

DICT_DB_PATH = "/opt/fleet/projects/japan/data/dict_index.sqlite3"
ANKI_DB_PATH = "/opt/japan/.local/share/Anki2/User 1/collection.anki2"
JAPAN_DIR = "/opt/fleet/projects/japan/japanese"


def bootstrap_kanji(conn: sqlite3.Connection, aconn: sqlite3.Connection) -> int:
    k_rows = conn.execute(
        "SELECT id, kanji, keyword, jlpt_level, on_reading, kun_reading, main_on_reading, diagram FROM kodansha_kanji"
    ).fetchall()
    img_map = {row[0]: row[1] for row in conn.execute("SELECT kanji, image FROM source_kanji_images").fetchall()}

    studied_kanji_reps: dict[str, tuple[int, int]] = {}
    anki_kanji_rows = aconn.execute(
        """
        SELECT n.flds, c.reps, c.mod
        FROM notes n
        JOIN cards c ON c.nid = n.id
        WHERE c.did IN (1757158925901, 1758314901201)
        """
    ).fetchall()
    for flds, reps, mod in anki_kanji_rows:
        k = flds.split("\x1f")[0].strip()
        if k and len(k) == 1:
            if k not in studied_kanji_reps or reps > studied_kanji_reps[k][0]:
                studied_kanji_reps[k] = (reps, mod)

    entries = []
    for kid, kanji, keyword, level, on_r, kun_r, main_on, diag in k_rows:
        kanji_char = kanji.strip()[0]
        img = img_map.get(kanji_char, "")
        reps, mod = studied_kanji_reps.get(kanji_char, (0, 0))
        is_target = 1 if (reps > 0 or level in ("N5", "N4", "N3", "N2", "N1")) else 0
        status = "studied" if reps > 0 else ("studying" if kanji_char in studied_kanji_reps else "unstudied")
        entries.append((kid, kanji_char, keyword, level, on_r, kun_r, main_on, diag, img, is_target, status, reps, mod))

    conn.executemany(
        """
        INSERT OR REPLACE INTO kanji_catalog
        (id, kanji, keyword, jlpt_level, on_reading, kun_reading, main_on_reading, diagram, image, is_study_target, status, reps, last_studied_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        entries,
    )
    return len(entries)


def bootstrap_grammar(conn: sqlite3.Connection, japan_dir: str) -> int:
    gp_path = os.path.join(japan_dir, "bunpro_grammar_points.json")
    prog_path = os.path.join(japan_dir, "grammar_progress.json")
    with open(gp_path, "r", encoding="utf-8") as f:
        points = json.load(f)

    studied_ids: set[int] = set()
    if os.path.isfile(prog_path):
        with open(prog_path, "r", encoding="utf-8") as f:
            prog = json.load(f)
            for lvl_pts in prog.get("studied_by_level", {}).values():
                for item in lvl_pts:
                    if "id" in item:
                        studied_ids.add(int(item["id"]))

    entries = []
    now = int(time.time())
    for pt in points:
        gid = pt["id"]
        is_studied = gid in studied_ids
        status = "studied" if is_studied else ("unlocked" if pt.get("level") in ("N5", "N4") else "locked")
        entries.append((
            gid, pt.get("level", "N5"), pt.get("title", ""), pt.get("meaning", ""),
            pt.get("category", ""), pt.get("url", ""), 1, status,
            pt.get("matched_sentences", 5 if is_studied else 0),
            pt.get("total_sentences", 5),
            now if is_studied else 0,
        ))

    conn.executemany(
        """
        INSERT OR REPLACE INTO bunpro_grammar_points
        (id, level, title, meaning, category, url, is_study_target, status, matched_sentences, total_sentences, studied_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        entries,
    )
    return len(entries)


def bootstrap_jlpt_vocab(conn: sqlite3.Connection, aconn: sqlite3.Connection, japan_dir: str) -> int:
    anki_vocab_reps: dict[str, int] = {}
    for flds, reps in aconn.execute(
        "SELECT n.flds, c.reps FROM notes n JOIN cards c ON c.nid = n.id WHERE c.did = 1759999324396"
    ).fetchall():
        clean_word = flds.split("\x1f")[0].replace("<ruby>", "").replace("</ruby>", "")
        clean_word = "".join(p.split("</rt>")[1] if "</rt>" in p else p for p in clean_word.split("<rt>"))
        if clean_word and reps > anki_vocab_reps.get(clean_word, -1):
            anki_vocab_reps[clean_word] = reps

    entries = []
    for lvl in ["n5", "n4", "n3", "n2", "n1"]:
        v_path = os.path.join(japan_dir, f"bunpro_{lvl}_vocab.json")
        if not os.path.isfile(v_path):
            continue
        with open(v_path, "r", encoding="utf-8") as f:
            v_list = json.load(f)
            for item in v_list:
                w = item.get("word", "")
                reps = anki_vocab_reps.get(w, 0)
                status = "studied" if reps > 0 else ("studying" if w in anki_vocab_reps else "unstudied")
                entries.append((item.get("id"), lvl.upper(), w, item.get("reading", ""), item.get("raw", ""), 1, status, reps))

    conn.executemany(
        "INSERT OR REPLACE INTO jlpt_vocab (vocab_id, level, word, reading, raw, is_study_target, status, reps) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        entries,
    )
    return len(entries)


def run_migration() -> None:
    print("Starting migration to unified SQLite study targets...")
    conn = sqlite3.connect(DICT_DB_PATH)
    aconn = sqlite3.connect(ANKI_DB_PATH)
    try:
        conn.execute("BEGIN")
        setup_tables(conn)
        k_cnt = bootstrap_kanji(conn, aconn)
        print(f"Bootstrapped {k_cnt} kanji into kanji_catalog")
        g_cnt = bootstrap_grammar(conn, JAPAN_DIR)
        print(f"Bootstrapped {g_cnt} grammar points into bunpro_grammar_points")
        v_cnt = bootstrap_jlpt_vocab(conn, aconn, JAPAN_DIR)
        print(f"Bootstrapped {v_cnt} vocab into jlpt_vocab")
        conn.execute("COMMIT")
        print("Migration committed successfully.")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
        aconn.close()


if __name__ == "__main__":
    run_migration()
