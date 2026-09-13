#!/usr/bin/env python3
"""
core/anki_cli.py — Intuitive CLI for Anki SRS status, sync, and rescheduling.
Strictly <= 200 lines invariant.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COL_PATH = Path("/opt/japan/.local/share/Anki2/User 1/collection.anki2")
VOCAB_DID = 1759999324396


def get_db() -> sqlite3.Connection:
    if not COL_PATH.is_file():
        sys.stderr.write(f"Error: collection not found at {COL_PATH}\n")
        sys.exit(1)
    conn = sqlite3.connect(COL_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def show_status() -> None:
    conn = get_db()
    cur = conn.cursor()
    col_row = cur.execute("SELECT crt, mod, scm, ver, usn FROM col").fetchone()
    crt_ts = col_row["crt"]
    now_ts = int(time.time())
    today_day = (now_ts - crt_ts) // 86400

    cur.execute("SELECT (SELECT count(*) FROM cards WHERE usn = -1), (SELECT count(*) FROM notes WHERE usn = -1)")
    uncommitted_cards, uncommitted_notes = cur.fetchone()

    cur.execute("""
        SELECT 
            did,
            sum(CASE WHEN queue = 0 THEN 1 ELSE 0 END) as q0,
            sum(CASE WHEN queue = 1 THEN 1 ELSE 0 END) as q1,
            sum(CASE WHEN queue = 2 AND due <= ? THEN 1 ELSE 0 END) as q2_due,
            sum(CASE WHEN queue = 2 AND due > ? THEN 1 ELSE 0 END) as q2_future,
            count(*) as total
        FROM cards
        GROUP BY did
    """, (today_day, today_day))
    deck_stats = {r["did"]: r for r in cur.fetchall()}

    cur.execute("SELECT id, name FROM decks")
    deck_names = {r["id"]: r["name"] for r in cur.fetchall()}
    conn.close()

    print("=" * 60)
    print(f"🎌 ANKI SRS STATUS — Day {today_day} ({time.strftime('%Y-%m-%d %H:%M')})")
    print(f"📦 Schema: v{col_row['ver']} | Uncommitted: {uncommitted_cards} cards, {uncommitted_notes} notes")
    print("=" * 60)

    for did, name in sorted(deck_names.items(), key=lambda x: x[1]):
        if did not in deck_stats:
            continue
        st = deck_stats[did]
        if st["total"] == 0:
            continue
        due_str = f"\033[1;31m{st['q2_due']} due\033[0m" if st["q2_due"] > 0 else "\033[1;32m0 due\033[0m"
        print(f"• {name[:38]:<38} : {st['q0']} new | {st['q1']} lrn | {due_str} | {st['q2_future']} fut (tot {st['total']})")

    print("=" * 60)


def trigger_sync() -> int:
    print("🚀 Triggering AnkiWeb sync...")
    t0 = time.time()
    sync_script = REPO_ROOT / "core" / "sync_and_push.py"
    try:
        from anki_sync.backup_sentinel import create_snapshot
        create_snapshot(str(COL_PATH))
    except Exception:
        pass
    cmd = [sys.executable, str(sync_script)]
    res = subprocess.run(cmd)
    elapsed = time.time() - t0
    if res.returncode == 0:
        print(f"✨ Sync completed successfully in {elapsed:.2f}s!")
    else:
        print(f"❌ Sync failed with exit code {res.returncode} ({elapsed:.2f}s).")
    return res.returncode


def run_integrity_check() -> int:
    try:
        from anki_sync.backup_sentinel import verify_collection_integrity, create_snapshot
        rep = verify_collection_integrity(str(COL_PATH))
        snap = create_snapshot(str(COL_PATH))
        print("=" * 60)
        print("🛡️ ANKI INTEGRITY & SNAPSHOT SENTINEL")
        print("=" * 60)
        print(f"• SQLite Integrity  : {rep.get('pragma_integrity')}")
        print(f"• Total Cards       : {rep.get('total_cards')}")
        print(f"• Orphan Cards      : {rep.get('orphan_cards')}")
        print(f"• Uncommitted Cards : {rep.get('uncommitted_cards')}")
        print(f"• Snapshot Created  : {snap}")
        print("=" * 60)
        return 0 if rep.get("healthy") else 1
    except Exception as e:
        print(f"❌ Integrity check failed: {e}")
        return 1


def reschedule_overdue(days: int = 14, deck_ids: list[int] | None = None) -> int:
    conn = get_db()
    cur = conn.cursor()
    col_row = cur.execute("SELECT crt FROM col").fetchone()
    today_day = (int(time.time()) - col_row["crt"]) // 86400
    target_dids = deck_ids or [1759999324396, 1757158925901, 1770845308673]

    placeholders = ",".join("?" for _ in target_dids)
    cur.execute(f"""
        SELECT id, did, queue, type, ivl, factor, lapses 
        FROM cards 
        WHERE did IN ({placeholders}) AND ((queue = 2 AND due <= ?) OR queue = 1)
        ORDER BY did ASC, ivl ASC, lapses DESC, id ASC
    """, (*target_dids, today_day))
    target_cards = cur.fetchall()

    if not target_cards:
        print(f"✅ No due or learning cards found across target decks for today (day {today_day}).")
        conn.close()
        return 0

    total = len(target_cards)
    print(f"🔄 Smoothing {total} remaining cards across {days} days (from day {today_day + 1} to {today_day + days})...")

    now_ts = int(time.time())
    now_ms = now_ts * 1000
    for idx, card in enumerate(target_cards):
        target_day = today_day + 1 + (idx % days)
        if card["queue"] == 1:
            factor = card["factor"] if card["factor"] > 0 else 2500
            ivl = max(card["ivl"], 1)
            cur.execute("""
                UPDATE cards 
                SET queue = 2, type = 2, ivl = ?, factor = ?, left = 0, due = ?, mod = ?, usn = -1 
                WHERE id = ?
            """, (ivl, factor, target_day, now_ts, card["id"]))
        else:
            cur.execute(
                "UPDATE cards SET due = ?, mod = ?, usn = -1 WHERE id = ?",
                (target_day, now_ts, card["id"]),
            )

    cur.execute(f"UPDATE col SET mod = {now_ms}, usn = -1")
    conn.commit()
    conn.close()

    print(f"✅ Successfully rescheduled {total} cards to future days! Pushing to AnkiWeb...")
    return trigger_sync()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Intuitive Anki CLI for Japan Studies")
    sub = parser.add_subparsers(dest="action", help="Action to execute")
    sub.add_parser("status", help="Show current SRS due status across decks")
    sub.add_parser("sync", help="Trigger AnkiWeb sync and pipeline update")
    sub.add_parser("check", help="Verify SQLite integrity and create an atomic snapshot backup")
    resch = sub.add_parser("reschedule", help="Evenly smooth overdue reviews across N days")
    resch.add_argument("--days", type=int, default=14, help="Number of days to spread over (default: 14)")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    action = args.action or "status"

    if action == "status":
        show_status()
        return 0
    elif action == "sync":
        return trigger_sync()
    elif action == "check":
        return run_integrity_check()
    elif action == "reschedule":
        return reschedule_overdue(args.days)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
