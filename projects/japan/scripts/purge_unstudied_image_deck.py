#!/usr/bin/env python3
"""
scripts/purge_unstudied_image_deck.py — Purge unstudied Kanji Image Deck cards.
Enforces deterministic gating: only genuinely studied kanji remain in Anki.
Strictly <= 200 lines invariant.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.db import open_anki_db, get_anki_db_path
from core.anki_sync.backup_sentinel import create_snapshot, verify_collection_integrity
from engine.study_queue import get_studied_kanji_set

KANJI_IMAGE_DID = 1757158925901
MIDNIGHT_TODAY = 1789728000000  # 2026-09-18 00:00:00 UTC


def purge_unstudied_cards() -> dict[str, int]:
    col_path = get_anki_db_path()
    print(f"[*] Collection path: {col_path}")

    # 1. Snapshot backup
    snap = create_snapshot(col_path)
    print(f"[+] Created safety snapshot: {snap}")

    conn = open_anki_db(timeout=30.0)
    cur = conn.cursor()

    # 2. Fetch all cards in Kanji Image Deck
    cur.execute(
        "SELECT c.id, c.nid, n.flds FROM cards c JOIN notes n ON c.nid = n.id WHERE c.did = ?",
        (KANJI_IMAGE_DID,)
    )
    cards = cur.fetchall()
    cids = {c[0]: c for c in cards}
    print(f"[*] Total cards in deck {KANJI_IMAGE_DID}: {len(cards)}")

    # 3. Stream revlog to find historical human study before today
    cur.execute("SELECT cid, time, id FROM revlog")
    historical_studied_cids = set()
    for cid, t, rid in cur.fetchall():
        if cid in cids and t > 0 and rid < MIDNIGHT_TODAY:
            historical_studied_cids.add(cid)

    to_delete = []
    to_delete_kanji = []

    for cid, nid, flds in cards:
        if cid not in historical_studied_cids:
            to_delete.append((cid, nid))
            kanji_char = flds.split("\x1f")[0].strip()
            to_delete_kanji.append(kanji_char)

    print(f"[*] Cards to keep (genuinely studied): {len(cards) - len(to_delete)}")
    print(f"[*] Cards to purge (never studied / dummy import): {len(to_delete)}")

    if not to_delete:
        print("[!] No unstudied cards to delete.")
        conn.close()
        return {"total": len(cards), "kept": len(cards), "purged": 0}

    # 4. Perform ultra-fast atomic deletion using TEMP table
    cur.execute("CREATE TEMP TABLE _purge_ids (cid INTEGER PRIMARY KEY, nid INTEGER)")
    cur.executemany("INSERT INTO _purge_ids (cid, nid) VALUES (?, ?)", to_delete)

    cur.execute("DELETE FROM revlog WHERE cid IN (SELECT cid FROM _purge_ids)")
    cur.execute("DELETE FROM cards WHERE id IN (SELECT cid FROM _purge_ids)")
    cur.execute("DELETE FROM notes WHERE id IN (SELECT nid FROM _purge_ids)")
    cur.execute("DROP TABLE _purge_ids")

    # 5. Update collection metadata
    now_ms = int(time.time() * 1000)
    cur.execute("UPDATE col SET mod = ?, usn = -1", (now_ms,))

    conn.commit()
    conn.close()

    # 6. Verify integrity
    integ = verify_collection_integrity(col_path)
    print(f"[+] Post-purge integrity check: {integ.get('healthy', False)}")
    if not integ.get("healthy"):
        raise RuntimeError(f"Database integrity compromised: {integ}")

    # 7. Refresh studied kanji cache
    studied_set = get_studied_kanji_set(refresh=True)
    print(f"[+] Refreshed studied kanji cache: {len(studied_set)} mature kanji.")

    return {
        "total": len(cards),
        "kept": len(cards) - len(to_delete),
        "purged": len(to_delete),
        "sample_purged": to_delete_kanji[:10]
    }


if __name__ == "__main__":
    res = purge_unstudied_cards()
    print("\n" + "=" * 50)
    print(f"✨ Purge complete: {res['purged']} cards deleted, {res['kept']} retained.")
    print("=" * 50)
