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
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.db import open_anki_db, get_anki_db_path

COL_PATH = Path(get_anki_db_path())
VOCAB_DID = 1759999324396


def get_db() -> sqlite3.Connection:
    conn = open_anki_db(timeout=15.0)
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
    try:
        from anki_sync.backup_sentinel import create_snapshot
        create_snapshot(str(COL_PATH))
    except Exception:
        pass
    res = subprocess.run([sys.executable, str(REPO_ROOT / "core" / "sync_and_push.py")])
    elapsed = time.time() - t0
    print(f"{'✨ Sync completed successfully' if res.returncode == 0 else '❌ Sync failed'} in {elapsed:.2f}s!")
    return res.returncode


def run_integrity_check() -> int:
    try:
        from anki_sync.backup_sentinel import verify_collection_integrity, create_snapshot
        rep, snap = verify_collection_integrity(str(COL_PATH)), create_snapshot(str(COL_PATH))
        print("=" * 60 + "\n🛡️ ANKI INTEGRITY & SNAPSHOT SENTINEL\n" + "=" * 60)
        print(f"• SQLite Integrity  : {rep.get('pragma_integrity')}\n• Total Cards       : {rep.get('total_cards')}\n• Snapshot Created  : {snap}\n" + "=" * 60)
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


def run_fsrs_recalibration(retention: float = 0.90) -> int:
    try:
        from core.fsrs_daemon import run_daily_fsrs_recalibration
        res = run_daily_fsrs_recalibration(target_retention=retention, apply_to_anki=True)
        print(f"✨ FSRS recalibration complete! {res['calibrated_cards']} cards, {res['updated_factors']} factors updated ({res['elapsed_s']}s).")
        return trigger_sync() if res.get("updated_factors", 0) > 0 else 0
    except Exception as e:
        print(f"❌ FSRS recalibration failed: {e}")
        return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Intuitive Anki CLI for Japan Studies")
    sub = p.add_subparsers(dest="action", help="Action to execute")
    sub.add_parser("status", help="Show current SRS due status across decks")
    sub.add_parser("sync", help="Trigger AnkiWeb sync and pipeline update")
    sub.add_parser("check", help="Verify SQLite integrity and create an atomic snapshot backup")
    resch = sub.add_parser("reschedule", help="Evenly smooth overdue reviews across N days")
    resch.add_argument("--days", type=int, default=14, help="Days to spread over")
    fsrs_p = sub.add_parser("fsrs", help="Recalibrate FSRS weights & card memory states")
    fsrs_p.add_argument("--retention", type=float, default=0.90, help="Target retention (default 0.90)")
    return p


def main() -> int:
    args = build_parser().parse_args()
    act = args.action or "status"
    if act == "status": return show_status() or 0
    elif act == "sync": return trigger_sync()
    elif act == "check": return run_integrity_check()
    elif act == "reschedule": return reschedule_overdue(args.days)
    elif act == "fsrs": return run_fsrs_recalibration(args.retention)
    return 0


if __name__ == "__main__":
    sys.exit(main())
