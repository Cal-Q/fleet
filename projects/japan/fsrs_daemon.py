#!/usr/bin/env python3
"""
core/fsrs_daemon.py — Autonomous Daily FSRS Recalibration & Memory Daemon
Recalibrates FSRS weights per deck and recalculates Stability, Difficulty, Retrievability per card.
Strictly <= 200 lines invariant.
"""

import json
import math
import os
import sqlite3
import sys
import time
from typing import Any, Dict, List, Tuple

BASE_DIR = "/opt/japan"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.db import open_anki_db
from core.fsrs_model import (
    DEFAULT_WEIGHTS, step_card_fsrs, calculate_retrievability, calculate_interval
)
from core.fsrs_optimizer import optimize_deck_weights, save_deck_weights

CARD_STATES_FILE = os.path.join(BASE_DIR, "japanese", "fsrs_card_states.json")


def load_card_states() -> Dict[str, Any]:
    if os.path.exists(CARD_STATES_FILE):
        try:
            with open(CARD_STATES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_card_states(states: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(CARD_STATES_FILE), exist_ok=True)
    with open(CARD_STATES_FILE, "w", encoding="utf-8") as f:
        json.dump(states, f, ensure_ascii=False, indent=2)


def run_daily_fsrs_recalibration(
    target_retention: float = 0.90, apply_to_anki: bool = True
) -> Dict[str, Any]:
    print(f"[*] Starting Daily FSRS Recalibration Daemon (Target Retention: {target_retention * 100:.0f}%)...")
    t0 = time.time()
    conn = open_anki_db(timeout=30.0)
    cur = conn.cursor()

    cur.execute("SELECT crt FROM col")
    crt_ts = cur.fetchone()[0]
    now_ts = int(time.time())
    today_days = (now_ts - crt_ts) // 86400

    cur.execute("SELECT id, name FROM decks WHERE id != 1")
    decks = cur.fetchall()

    # 1. Per-Deck Weight Optimization
    print("[1/3] Optimizing FSRS weight vectors per deck...")
    deck_reports = {}
    for did, raw_name in decks:
        name = raw_name.replace("\x1f", "::")
        report = optimize_deck_weights(conn, did, name)
        deck_reports[str(did)] = report
        print(f"  • Deck {name[:32]:<32} : {report['sample_reviews']:>5} revs | loss {report['log_loss']:.4f} | status: {report['status'][:20]}")
    save_deck_weights(deck_reports)

    # 2. Per-Card Stability & Difficulty Recalibration
    print("[2/3] Reconstructing memory state (S, D, R) for every card...")
    cur.execute("""
        SELECT r.cid, r.id, r.ease, r.type
        FROM revlog r
        JOIN cards c ON r.cid = c.id
        WHERE r.ease BETWEEN 1 AND 4
        ORDER BY r.cid ASC, r.id ASC
    """)
    all_revs = cur.fetchall()

    card_rev_map: Dict[int, List[Tuple[int, int]]] = {}
    for cid, rev_time_ms, ease, _ in all_revs:
        if cid not in card_rev_map:
            card_rev_map[cid] = []
        card_rev_map[cid].append((rev_time_ms, ease))

    cur.execute("SELECT id, did, queue, type, ivl, factor, due, reps, lapses FROM cards WHERE queue != -1")
    all_cards = cur.fetchall()

    card_states = {}
    updated_cards = 0
    now_ms = now_ts * 1000

    for cid, did, queue, c_type, curr_ivl, curr_factor, curr_due, reps, lapses in all_cards:
        deck_w = deck_reports.get(str(did), {}).get("weights", DEFAULT_WEIGHTS)
        revs = card_rev_map.get(cid, [])
        s, d = 0.0, 0.0

        if revs:
            last_t = revs[0][0]
            s, d, _ = step_card_fsrs(s, d, 0.0, revs[0][1], deck_w)
            for t_ms, ease in revs[1:]:
                elapsed = max(0.1, (t_ms - last_t) / (86400.0 * 1000.0))
                s, d, _ = step_card_fsrs(s, d, elapsed, ease, deck_w)
                last_t = t_ms
            elapsed_since_last = max(0.0, (now_ms - last_t) / (86400.0 * 1000.0))
            r_today = calculate_retrievability(elapsed_since_last, s)
        else:
            r_today = 1.0 if queue == 0 else 0.90

        optimal_ivl = calculate_interval(s, target_retention)
        card_states[str(cid)] = {
            "stability": round(s, 2), "difficulty": round(d, 2),
            "retrievability": round(r_today, 4), "optimal_ivl": optimal_ivl,
            "reps": reps, "lapses": lapses, "did": did
        }

        if apply_to_anki and queue == 2:
            new_factor = max(1300, min(3500, int(round(2500 - (d - 5.0) * 200))))
            if abs(new_factor - (curr_factor or 2500)) > 50:
                cur.execute("UPDATE cards SET factor = ?, mod = ?, usn = -1 WHERE id = ?", (new_factor, now_ts, cid))
                updated_cards += 1

    save_card_states(card_states)
    if apply_to_anki and updated_cards > 0:
        cur.execute("UPDATE col SET mod = ?, usn = -1", (now_ms,))
        conn.commit()

    conn.close()
    elapsed_total = time.time() - t0
    print(f"[3/3] Complete! {len(card_states)} cards calibrated ({updated_cards} factor updates) in {elapsed_total:.2f}s.")

    return {
        "status": "ok", "calibrated_cards": len(card_states),
        "updated_factors": updated_cards, "decks_optimized": len(deck_reports),
        "elapsed_s": round(elapsed_total, 2), "target_retention": target_retention
    }


if __name__ == "__main__":
    retention = float(sys.argv[1]) if len(sys.argv) > 1 else 0.90
    res = run_daily_fsrs_recalibration(target_retention=retention)
    print(json.dumps(res, indent=2))
