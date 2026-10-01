#!/usr/bin/env python3
"""
core/anki_scheduler.py — Authentic Scheduler Review State Machine for Anki SQLite
Handles interval transitions, ease factors, card queues, and revlog inserts.
Strictly <= 200 lines, <= 100 cols invariant.
"""

import time
import sqlite3
from typing import Any, Dict


def get_today_days(cur: sqlite3.Cursor) -> int:
    cur.execute("SELECT crt FROM col")
    row = cur.fetchone()
    crt = row[0] if row else 1734058800
    return int((time.time() - crt) // 86400)


def calculate_intervals_for_card(
    c_type: int, queue: int, ivl: int, factor: int
) -> Dict[str, str]:
    if queue == 0 or c_type == 0:
        return {"again": "<10m", "hard": "1g", "good": "1g", "easy": "4g"}
    elif queue == 1 or c_type == 1:
        return {"again": "<10m", "hard": "1g", "good": "1g", "easy": "4g"}
    else:
        ivl_val = max(1, ivl)
        f_mult = max(1.3, factor / 1000.0)
        return {
            "again": "<10m",
            "hard": f"{max(1, int(ivl_val * 1.2))}g",
            "good": f"{max(1, int(round(ivl_val * f_mult)))}g",
            "easy": f"{max(2, int(round(ivl_val * f_mult * 1.3)))}g",
        }


def apply_card_review(
    conn: sqlite3.Connection,
    cid: int,
    grade: int,
    time_taken_ms: int = 0,
    review_time_ms: int = 0
) -> Dict[str, Any]:
    """
    Applies Anki card grading (1=Wrong/Again, 2=Hard, 3=Correct/Good, 4=Easy)
    to a card, updating cards table and inserting a revlog record.
    """
    cur = conn.cursor()
    now_ts = int(time.time())
    cur.execute("SELECT max(id) FROM revlog")
    max_row = cur.fetchone()
    max_id = max_row[0] if max_row and max_row[0] else 0
    now_ms = max(int(time.time() * 1000), max_id + 1, review_time_ms or 0)
    today_days = get_today_days(cur)

    cur.execute(
        "SELECT id, nid, did, ord, mod, usn, type, queue, due, ivl, factor, reps, lapses, left "
        "FROM cards WHERE id = ?",
        (cid,)
    )
    row = cur.fetchone()
    if not row:
        return {"status": "error", "message": "Card not found"}

    (
        c_id, nid, did, ord_v, _, _,
        c_type, queue, due, ivl, factor, reps, lapses, left_v
    ) = row

    last_ivl = ivl
    factor = factor if factor and factor > 0 else 2500
    reps = reps + 1
    new_factor = factor
    new_type = c_type
    new_queue = queue
    new_due = due
    new_ivl = ivl
    rev_type = 1 if c_type == 2 else 0

    is_leech = False
    if grade == 1:  # WRONG / AGAIN
        if queue == 2:
            # Mature review lapse: increment lapses once, reduce factor, enter relearning
            lapses += 1
            new_factor = max(1300, factor - 200)
            if lapses >= 8:
                # LEECH: 8 or more lapses -> auto-suspend for 30-day quarantine
                new_queue = -1
                new_ivl = 0
                new_due = 0
                rev_type = 2
                is_leech = True
            else:
                new_type = 1
                new_queue = 1
                new_ivl = 0
                new_due = now_ts + 600
                rev_type = 2
        else:
            # New or already in Learning: remains in learning queue, no lapse increase
            new_type = 1
            new_queue = 1
            new_ivl = 0
            new_due = now_ts + 60
            rev_type = 0
    else:  # CORRECT / GOOD / EASY (grade >= 2)
        if c_type == 0 or queue == 0:  # Graduating New card
            new_type = 2
            new_queue = 2
            new_ivl = 1 if grade == 3 else (4 if grade == 4 else 1)
            new_due = today_days + new_ivl
        elif c_type == 1 or queue == 1:  # Graduating Learning card
            new_type = 2
            new_queue = 2
            new_ivl = 1 if grade == 3 else (4 if grade == 4 else 1)
            new_due = today_days + new_ivl
        else:  # Review card success
            new_type = 2
            new_queue = 2
            f_mult = max(1.3, factor / 1000.0)
            if grade == 2:  # Hard
                new_factor = max(1300, factor - 150)
                new_ivl = max(1, int(round(ivl * 1.2)))
            elif grade == 4:  # Easy
                new_factor = factor + 150
                new_ivl = max(2, int(round(ivl * f_mult * 1.3)))
            else:  # Good (grade == 3)
                new_ivl = max(1, int(round(ivl * f_mult)))
            new_due = today_days + new_ivl

    # 1. Update Card in SQLite
    cur.execute(
        """
        UPDATE cards
        SET mod = ?, usn = -1, type = ?, queue = ?, due = ?,
            ivl = ?, factor = ?, reps = ?, lapses = ?
        WHERE id = ?
        """,
        (now_ts, new_type, new_queue, new_due, new_ivl, new_factor, reps, lapses, cid)
    )

    # 2. If card became a leech, tag the note
    if is_leech:
        cur.execute("SELECT tags FROM notes WHERE id = ?", (nid,))
        trow = cur.fetchone()
        cur_tags = (trow[0] if trow and trow[0] else "").split()
        if "leech" not in cur_tags:
            new_tags = f"{trow[0] if trow and trow[0] else ''} leech".strip()
            cur.execute(
                "UPDATE notes SET tags = ?, usn = -1, mod = ? WHERE id = ?",
                (new_tags, now_ts, nid)
            )

    # 3. Insert into Revlog
    cur.execute(
        """
        INSERT OR REPLACE INTO revlog (id, cid, usn, ease, ivl, lastIvl, factor, time, type)
        VALUES (?, ?, -1, ?, ?, ?, ?, ?, ?)
        """,
        (now_ms, cid, grade, new_ivl, last_ivl, new_factor, max(1000, time_taken_ms), rev_type)
    )

    # 4. Mark Collection as modified for sync
    cur.execute("UPDATE col SET mod = ?, usn = -1", (now_ms,))
    conn.commit()

    return {
        "status": "ok",
        "card_id": cid,
        "new_queue": new_queue,
        "new_ivl": new_ivl,
        "new_due": new_due,
        "reps": reps,
        "lapses": lapses,
        "is_leech": is_leech,
    }
