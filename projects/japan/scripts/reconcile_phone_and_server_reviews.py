#!/usr/bin/env python3
"""
scripts/reconcile_phone_and_server_reviews.py — Reconcile AnkiDroid & Server Reviews
Merges missing reviews from phone AnkiDroid SQLite into workspace DB and resolves duplicates.
Strictly <= 200 lines invariant.
"""

import os
import sqlite3
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BASE_DIR)

from core.anki_sync.backup_sentinel import create_snapshot, verify_collection_integrity
from core.db import open_anki_db

PHONE_COL_REMOTE = "/sdcard/AnkiDroid/collection.anki2"
TEMP_PHONE_COL = os.path.join(BASE_DIR, "data", "phone_col_temp.anki2")


def pull_phone_database() -> bool:
    print("[*] 1. Pulling /sdcard/AnkiDroid/collection.anki2 from Redmi Note 7...")
    res = subprocess.run(["scp", f"redmi:{PHONE_COL_REMOTE}", TEMP_PHONE_COL], capture_output=True)
    return res.returncode == 0 and os.path.isfile(TEMP_PHONE_COL)


def reconcile_reviews() -> int:
    col_path = os.path.join(BASE_DIR, ".local/share/Anki2/User 1/collection.anki2")
    snap = create_snapshot(col_path)
    print(f"[*] 2. Created safety snapshot: {snap}")

    ws_conn = open_anki_db()
    ws_cur = ws_conn.cursor()

    phone_conn = sqlite3.connect(TEMP_PHONE_COL)
    phone_cur = phone_conn.cursor()

    # Get missing revlog entries from phone
    ws_cur.execute("SELECT id FROM revlog WHERE id >= 1789500000000")
    ws_rev_ids = {r[0] for r in ws_cur.fetchall()}

    phone_cur.execute(
        "SELECT id, cid, usn, ease, ivl, lastIvl, factor, time, type "
        "FROM revlog WHERE id >= 1789500000000 ORDER BY id ASC"
    )
    phone_revs = phone_cur.fetchall()
    missing_revs = [r for r in phone_revs if r[0] not in ws_rev_ids]
    print(f"[*] 3. Found {len(missing_revs)} missing revlogs on phone to merge.")

    # Insert missing revlogs into workspace DB
    ws_cur.executemany(
        "INSERT OR IGNORE INTO revlog (id, cid, usn, ease, ivl, lastIvl, factor, time, type) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        missing_revs
    )

    # Reconcile cards
    sept17_start = int(time.mktime(time.strptime("2026-09-17 00:00:00", "%Y-%m-%d %H:%M:%S")) * 1000)
    sept17_end = int(time.mktime(time.strptime("2026-09-17 23:59:59", "%Y-%m-%d %H:%M:%S")) * 1000)
    sept18_start = int(time.mktime(time.strptime("2026-09-18 00:00:00", "%Y-%m-%d %H:%M:%S")) * 1000)

    phone_cids = {r[1] for r in missing_revs}
    fixed_cards = 0

    for cid in phone_cids:
        # Check phone card state
        phone_cur.execute(
            "SELECT due, ivl, factor, reps, lapses, queue, type, mod "
            "FROM cards WHERE id = ?", (cid,)
        )
        p_row = phone_cur.fetchone()
        if not p_row:
            continue
        p_due, p_ivl, p_factor, p_reps, p_lapses, p_queue, p_type, p_mod = p_row

        # Check reviews in workspace for today
        ws_cur.execute(
            "SELECT id, ease, ivl, lastIvl FROM revlog WHERE cid = ? AND id >= ? ORDER BY id DESC",
            (cid, sept18_start)
        )
        today_revs = ws_cur.fetchall()

        if today_revs:
            # Card was reviewed yesterday on phone AND today on WS due to desync
            # If the phone review was for a mature card (p_ivl > 1), it was not actually due today.
            # Restore authentic interval from phone review
            p_last_rev = [r for r in phone_revs if r[1] == cid and sept17_start <= r[0] <= sept17_end]
            if p_last_rev and p_ivl > 1:
                # Authentic due date scheduled on Sept 17 (day 643) + interval
                true_due = 643 + p_ivl
                ws_cur.execute(
                    "UPDATE cards SET due = ?, ivl = ?, factor = ?, reps = ?, lapses = ?, queue = 2, type = 2, mod = ?, usn = -1 WHERE id = ?",
                    (true_due, p_ivl, p_factor, p_reps, p_lapses, int(time.time()), cid)
                )
                fixed_cards += 1
        else:
            # Card was reviewed yesterday on phone and not yet in WS: apply phone state
            ws_cur.execute(
                "UPDATE cards SET due = ?, ivl = ?, factor = ?, reps = ?, lapses = ?, queue = ?, type = ?, mod = ?, usn = -1 WHERE id = ?",
                (p_due, p_ivl, p_factor, p_reps, p_lapses, p_queue, p_type, int(time.time()), cid)
            )
            fixed_cards += 1

    # Update collection timestamp
    now_ms = int(time.time() * 1000)
    ws_cur.execute("UPDATE col SET mod = ?, usn = -1", (now_ms,))
    ws_conn.commit()
    ws_conn.close()
    phone_conn.close()

    print(f"[*] 4. Reconciled {fixed_cards} card states in workspace DB.")
    return fixed_cards


def push_reconciled_db() -> bool:
    col_path = os.path.join(BASE_DIR, ".local/share/Anki2/User 1/collection.anki2")
    diag = verify_collection_integrity(col_path)
    print(f"[*] 5. Workspace DB Integrity: {diag}")
    if not diag.get("healthy"):
        print("[!] ERROR: Workspace DB failed integrity verification!")
        return False

    print("[*] 6. Pushing reconciled collection.anki2 to Redmi Note 7...")
    res1 = subprocess.run(["scp", col_path, f"redmi:{PHONE_COL_REMOTE}"], capture_output=True)
    res2 = subprocess.run(["ssh", "redmi", f"cp {PHONE_COL_REMOTE} /data/data/com.termux/files/home/japan/collection.anki2"], capture_output=True)
    if os.path.exists(TEMP_PHONE_COL):
        os.remove(TEMP_PHONE_COL)
    return res1.returncode == 0 and res2.returncode == 0


if __name__ == "__main__":
    if not pull_phone_database():
        print("[!] Failed to pull phone database")
        sys.exit(1)
    cnt = reconcile_reviews()
    if push_reconciled_db():
        print(f"[✓] SUCCESS: Reconciled {cnt} cards. Both phone and server are 100% in sync!")
    else:
        print("[!] Failed to push reconciled database")
        sys.exit(1)
