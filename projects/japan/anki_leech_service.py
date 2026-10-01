#!/usr/bin/env python3
"""
core/anki_leech_service.py — Direct SQLite Leech Lifecycle & Quarantine Engine
Automates 30-day quarantine for leeches (>= 8 lapses) and rehabilitation.
Strictly <= 200 lines invariant.
"""

import time
import sqlite3
from typing import Any, Dict, List


def get_today_days(cur: sqlite3.Cursor) -> int:
    cur.execute("SELECT crt FROM col")
    row = cur.fetchone()
    crt = row[0] if row else 1734058800
    return int((time.time() - crt) // 86400)


def suspend_active_leeches(conn: sqlite3.Connection, threshold: int = 8) -> List[int]:
    """Finds all cards with lapses >= threshold that are still active and suspends them."""
    cur = conn.cursor()
    now_ts = int(time.time())

    cur.execute(
        """
        SELECT c.id, c.nid, n.tags
        FROM cards c
        JOIN notes n ON c.nid = n.id
        WHERE c.queue != -1 AND c.lapses >= ?
        """,
        (threshold,)
    )
    rows = cur.fetchall()
    suspended_cids: List[int] = []

    for cid, nid, tags in rows:
        cur.execute(
            "UPDATE cards SET queue = -1, usn = -1, mod = ? WHERE id = ?",
            (now_ts, cid)
        )
        cur_tags = (tags or "").split()
        if "leech" not in cur_tags:
            new_tags = f"{tags or ''} leech".strip()
            cur.execute("UPDATE notes SET tags = ?, usn = -1, mod = ? WHERE id = ?", (new_tags, now_ts, nid))
        suspended_cids.append(cid)

    return suspended_cids


def rehabilitate_matured_leeches(conn: sqlite3.Connection, cooldown_days: int = 30) -> List[Dict[str, Any]]:
    """Finds suspended cards whose last review was >= cooldown_days ago and rehabilitates them."""
    cur = conn.cursor()
    now_ts = int(time.time())
    now_ms = int(time.time() * 1000)
    cooldown_ms = cooldown_days * 86400 * 1000
    today_days = get_today_days(cur)

    cur.execute(
        """
        SELECT c.id, c.nid, c.did, max(r.id) as last_rev, n.tags, n.flds
        FROM cards c
        JOIN notes n ON c.nid = n.id
        LEFT JOIN revlog r ON r.cid = c.id
        WHERE c.queue = -1
        GROUP BY c.id
        """
    )
    rows = cur.fetchall()
    rehabilitated: List[Dict[str, Any]] = []

    for cid, nid, did, last_rev, tags, flds in rows:
        ref_ms = last_rev if last_rev else cid
        elapsed_ms = now_ms - ref_ms
        if elapsed_ms >= cooldown_ms:
            # Rehabilitate: queue=2, type=2, ivl=1, factor=1500, lapses=0, due=tomorrow
            cur.execute(
                """
                UPDATE cards
                SET queue = 2, type = 2, ivl = 1, factor = 1500, lapses = 0, due = ?, usn = -1, mod = ?
                WHERE id = ?
                """,
                (today_days + 1, now_ts, cid)
            )
            # Strip 'leech' tag from note
            cur_tags = [t for t in (tags or "").split() if t != "leech"]
            cleaned_tags = " ".join(cur_tags)
            cur.execute("UPDATE notes SET tags = ?, usn = -1, mod = ? WHERE id = ?", (cleaned_tags, now_ts, nid))

            word = flds.split("\x1f")[0] if flds else str(cid)
            rehabilitated.append({
                "card_id": cid,
                "note_id": nid,
                "deck_id": did,
                "word": word,
                "days_offline": round(elapsed_ms / (86400 * 1000), 1)
            })

    return rehabilitated


def run_leech_lifecycle(conn: sqlite3.Connection, cooldown_days: int = 30, threshold: int = 8) -> Dict[str, Any]:
    """Executes full leech lifecycle: auto-suspend new leeches and rehabilitate matured cards."""
    now_ms = int(time.time() * 1000)
    cur = conn.cursor()

    # 1. Rehabilitate first (cards that completed their 30-day rest)
    rehab_cards = rehabilitate_matured_leeches(conn, cooldown_days=cooldown_days)

    # 2. Suspend active cards that exceed lapse threshold
    new_suspended = suspend_active_leeches(conn, threshold=threshold)

    # 3. Mark collection modified
    if rehab_cards or new_suspended:
        cur.execute("UPDATE col SET mod = ?, usn = -1", (now_ms,))
        conn.commit()

    return {
        "status": "ok",
        "rehabilitated_count": len(rehab_cards),
        "rehabilitated_cards": rehab_cards,
        "suspended_count": len(new_suspended),
        "suspended_cids": new_suspended,
        "cooldown_days": cooldown_days,
        "threshold": threshold,
    }
