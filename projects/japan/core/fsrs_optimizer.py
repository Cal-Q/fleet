#!/usr/bin/env python3
"""
core/fsrs_optimizer.py — Per-Deck FSRS Weight Parameter Optimizer
Optimizes FSRS weights by minimizing Binary Cross-Entropy (log-loss) on Anki revlog.
Strictly <= 200 lines invariant.
"""

import json
import math
import os
import sqlite3
import sys
from typing import Any, Dict, List, Tuple

BASE_DIR = "/opt/japan"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.fsrs_model import DEFAULT_WEIGHTS, step_card_fsrs, calculate_retrievability

WEIGHTS_FILE = os.path.join(BASE_DIR, "japanese", "fsrs_deck_weights.json")


def load_deck_weights() -> Dict[str, List[float]]:
    if os.path.exists(WEIGHTS_FILE):
        try:
            with open(WEIGHTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_deck_weights(weights_by_deck: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(WEIGHTS_FILE), exist_ok=True)
    with open(WEIGHTS_FILE, "w", encoding="utf-8") as f:
        json.dump(weights_by_deck, f, ensure_ascii=False, indent=2)


def extract_deck_review_sequences(
    conn: sqlite3.Connection, did: int, limit: int = 5000
) -> List[List[Tuple[float, int]]]:
    """
    Extracts chronological review sequences (elapsed_days, grade) per card for a deck (most recent N).
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT r.cid, r.id, r.ease, r.type
        FROM revlog r
        JOIN cards c ON r.cid = c.id
        WHERE c.did = ? AND r.ease BETWEEN 1 AND 4
        ORDER BY r.id DESC
        LIMIT ?
    """, (did, limit))
    rows = cur.fetchall()

    card_reviews: Dict[int, List[Tuple[int, int]]] = {}
    for cid, rev_time_ms, ease, _ in sorted(rows, key=lambda x: (x[0], x[1])):
        if cid not in card_reviews:
            card_reviews[cid] = []
        card_reviews[cid].append((rev_time_ms, ease))

    sequences: List[List[Tuple[float, int]]] = []
    for cid, r_list in card_reviews.items():
        if len(r_list) < 2:
            continue
        seq = []
        last_time = r_list[0][0]
        for t_ms, ease in r_list[1:]:
            elapsed_days = max(0.1, (t_ms - last_time) / (86400.0 * 1000.0))
            seq.append((elapsed_days, ease))
            last_time = t_ms
        if seq:
            sequences.append(seq)
    return sequences


def evaluate_fsrs_loss(
    weights: List[float], sequences: List[List[Tuple[float, int]]]
) -> Tuple[float, float, int]:
    """
    Calculates Binary Cross Entropy Loss and RMSE on predicted Retrievability R vs actual outcome.
    """
    if not sequences:
        return 0.0, 0.0, 0
    total_loss, total_sq_err, total_count = 0.0, 0.0, 0
    eps = 1e-5

    for seq in sequences:
        s, d = 0.0, 0.0
        for elapsed, grade in seq:
            if s <= 0.0:
                s, d, _ = step_card_fsrs(s, d, 0.0, grade, weights)
                continue
            r = calculate_retrievability(elapsed, s)
            y = 1.0 if grade >= 2 else 0.0
            p = max(eps, min(1.0 - eps, r))
            loss = -(y * math.log(p) + (1.0 - y) * math.log(1.0 - p))
            total_loss += loss
            total_sq_err += (y - r) ** 2
            total_count += 1
            s, d, _ = step_card_fsrs(s, d, elapsed, grade, weights)

    if total_count == 0:
        return 0.0, 0.0, 0
    bce = total_loss / total_count
    rmse = math.sqrt(total_sq_err / total_count)
    return bce, rmse, total_count


def optimize_deck_weights(
    conn: sqlite3.Connection, did: int, deck_name: str = ""
) -> Dict[str, Any]:
    sequences = extract_deck_review_sequences(conn, did)
    if len(sequences) < 20:
        bce, rmse, cnt = evaluate_fsrs_loss(DEFAULT_WEIGHTS, sequences)
        return {
            "did": did, "name": deck_name, "sample_reviews": cnt,
            "weights": list(DEFAULT_WEIGHTS), "log_loss": round(bce, 4),
            "rmse": round(rmse, 4), "status": "default_weights_fallback (insufficient data)"
        }

    try:
        from scipy.optimize import minimize
        base_w = list(DEFAULT_WEIGHTS)

        def objective(sub_params: List[float]) -> float:
            test_w = list(base_w)
            test_w[0:4] = [max(0.05, p) for p in sub_params[0:4]]  # Stabilities
            test_w[4] = max(1.0, min(10.0, sub_params[4]))        # Base Difficulty
            test_w[8] = max(0.1, sub_params[5])                   # Stability Growth
            test_w[15] = max(0.1, sub_params[6])                  # Hard penalty
            test_w[16] = max(1.0, sub_params[7])                  # Easy bonus
            loss, _, _ = evaluate_fsrs_loss(test_w, sequences)
            return loss

        init_params = [base_w[0], base_w[1], base_w[2], base_w[3], base_w[4], base_w[8], base_w[15], base_w[16]]
        res = minimize(objective, init_params, method="Nelder-Mead", options={"maxiter": 60, "disp": False})

        opt_w = list(base_w)
        if res.success or res.fun < evaluate_fsrs_loss(base_w, sequences)[0]:
            opt_w[0:4] = [round(max(0.05, p), 4) for p in res.x[0:4]]
            opt_w[4] = round(max(1.0, min(10.0, res.x[4])), 4)
            opt_w[8] = round(max(0.1, res.x[5]), 4)
            opt_w[15] = round(max(0.1, res.x[6]), 4)
            opt_w[16] = round(max(1.0, res.x[7]), 4)

        bce, rmse, cnt = evaluate_fsrs_loss(opt_w, sequences)
        return {
            "did": did, "name": deck_name, "sample_reviews": cnt,
            "weights": opt_w, "log_loss": round(bce, 4),
            "rmse": round(rmse, 4), "status": "optimized"
        }
    except Exception as e:
        bce, rmse, cnt = evaluate_fsrs_loss(DEFAULT_WEIGHTS, sequences)
        return {
            "did": did, "name": deck_name, "sample_reviews": cnt,
            "weights": list(DEFAULT_WEIGHTS), "log_loss": round(bce, 4),
            "rmse": round(rmse, 4), "status": f"fallback: {e}"
        }
