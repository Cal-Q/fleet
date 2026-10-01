#!/usr/bin/env python3
"""
core/anki_sync/restore_kanji_srs.py — Authoritative Revlog SRS State Restoration Engine
Reconstructs exact review state (queue, type, ivl, factor, reps, lapses, due, data)
from live revlog in collection.anki2 with fallback to snapshot.
Strictly <= 200 lines invariant.
"""

from __future__ import annotations

import os
import sqlite3
import time


def restore_srs_state(
    target_db: str = "/opt/japan/.local/share/Anki2/User 1/collection.anki2",
    snapshot_db: str = "/opt/japan/.local/share/Anki2/User 1/backups/snapshot_1789730739.anki2",
) -> dict[str, int]:
    if not os.path.exists(target_db):
        raise FileNotFoundError(f"Target DB not found: {target_db}")

    snap_map: dict[tuple[str, str], tuple[int, int, int, int, int, int, int, str]] = {}
    snap_suspended: set[tuple[str, str]] = set()

    if os.path.exists(snapshot_db):
        sconn = sqlite3.connect(snapshot_db)
        sconn.create_collation("unicase", lambda a, b: (a > b) - (a < b))
        for dname, flds, ctype, cqueue, cdue, civl, cfactor, creps, collapses, cdata in sconn.execute(
            """
            SELECT d.name, n.flds, c.type, c.queue, c.due, c.ivl, c.factor, c.reps, c.lapses, c.data
            FROM notes n JOIN cards c ON c.nid = n.id JOIN decks d ON d.id = c.did
            """
        ).fetchall():
            front = flds.split("\x1f")[0].strip()
            norm_deck = dname.replace("\x1f", " ")
            snap_map[(norm_deck, front)] = (ctype, cqueue, cdue, civl, cfactor, creps, collapses, cdata)
            if cqueue == -1:
                snap_suspended.add((norm_deck, front))
        sconn.close()

    tconn = sqlite3.connect(target_db)
    tconn.create_collation("unicase", lambda a, b: (a > b) - (a < b))
    cur_t = tconn.cursor()

    cur_t.execute("SELECT crt FROM col LIMIT 1;")
    crt = cur_t.fetchone()[0]
    now_ts = int(time.time())

    # Build revlog lookup by cid
    rev_map: dict[int, tuple[int, int, int, int, int, int]] = {}
    for row in cur_t.execute(
        """
        SELECT 
            c.id, stats.tot_reps, stats.tot_lapses, r.id, r.ivl, r.factor
        FROM cards c
        JOIN (
            SELECT cid, max(id) as max_id, count(*) as tot_reps, sum(case when ease=1 then 1 else 0 end) as tot_lapses
            FROM revlog GROUP BY cid
        ) stats ON stats.cid = c.id
        JOIN revlog r ON r.id = stats.max_id
        """
    ).fetchall():
        cid, tot_reps, tot_lapses, log_id, log_ivl, log_factor = row
        rev_map[cid] = (tot_reps, tot_lapses, log_id, log_ivl, log_factor)

    target_cards = cur_t.execute(
        """
        SELECT c.id, d.name, n.flds, c.type, c.queue, c.due, c.ivl, c.factor, c.reps, c.lapses, c.data
        FROM notes n JOIN cards c ON c.nid = n.id JOIN decks d ON d.id = c.did
        """
    ).fetchall()

    updates = []
    restored_count = 0

    for cid, dname, flds, ctype, cqueue, cdue, civl, cfactor, creps, collapses, cdata in target_cards:
        front = flds.split("\x1f")[0].strip()
        norm_deck = dname.replace("\x1f", " ")
        rev = rev_map.get(cid)

        if rev:
            tot_reps, tot_lapses, log_id, log_ivl, log_factor = rev
            review_day = (log_id // 1000 - crt) // 86400
            is_susp = (norm_deck, front) in snap_suspended
            if log_ivl > 0:
                t_type = 2
                t_queue = -1 if is_susp else 2
                t_due = review_day + log_ivl
                t_ivl = log_ivl
                t_factor = log_factor if log_factor > 0 else (cfactor if cfactor > 0 else 2500)
            else:
                t_type = 1
                t_queue = -1 if is_susp else 1
                t_due = cdue
                t_ivl = 0
                t_factor = log_factor if log_factor > 0 else 2500
            t_reps = tot_reps
            t_lapses = tot_lapses
            t_data = cdata
        else:
            snap = snap_map.get((norm_deck, front))
            if snap:
                t_type, t_queue, t_due, t_ivl, t_factor, t_reps, t_lapses, t_data = snap
                if t_reps <= 1 and t_ivl <= 1:
                    continue
            else:
                continue

        if (
            ctype != t_type
            or cqueue != t_queue
            or cdue != t_due
            or civl != t_ivl
            or cfactor != t_factor
            or creps != t_reps
            or collapses != t_lapses
        ):
            updates.append((t_type, t_queue, t_due, t_ivl, t_factor, t_reps, t_lapses, t_data, now_ts, cid))
            restored_count += 1

    if updates:
        cur_t.executemany(
            """
            UPDATE cards
            SET type = ?, queue = ?, due = ?, ivl = ?, factor = ?, reps = ?, lapses = ?, data = ?, mod = ?, usn = -1
            WHERE id = ?
            """,
            updates,
        )
        cur_t.execute("UPDATE col SET mod = ?, usn = -1 WHERE id = 1;", (now_ts * 1000,))
        tconn.commit()

    tconn.close()
    return {"restored": restored_count, "total_target": len(target_cards)}


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "/opt/japan/.local/share/Anki2/User 1/collection.anki2"
    snap = sys.argv[2] if len(sys.argv) > 2 else "/opt/japan/.local/share/Anki2/User 1/backups/snapshot_1789730739.anki2"
    res = restore_srs_state(target, snap)
    print(f"[+] Restored SRS state from revlog for {res['restored']}/{res['total_target']} cards")
