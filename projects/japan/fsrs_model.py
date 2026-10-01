#!/usr/bin/env python3
"""
core/fsrs_model.py — FSRS Memory Model Core (Difficulty, Stability, Retrievability)
Calculates exact DSR state, next intervals for target retention, and state transitions.
Strictly <= 200 lines invariant.
"""

import math
from typing import Dict, List, Tuple

# Default calibrated FSRS weights (19 parameters)
DEFAULT_WEIGHTS: List[float] = [
    0.4072, 1.1834, 3.1730, 15.6910,  # 0..3: Initial Stability for Again, Hard, Good, Easy
    7.1949, 0.5345,                   # 4..5: Initial Difficulty base and rating multiplier
    1.4604, 0.0046,                   # 6..7: Mean reversion and difficulty damping
    1.5457, 0.1192, 1.0192,           # 8..10: Recall stability multipliers
    1.9395, 0.1100, 0.2960, 0.2269,   # 11..14: Lapse stability multipliers
    0.2315, 2.9898,                   # 15..16: Hard & Easy bonuses
    0.5165, 0.6621                    # 17..18: Decay & scaling factors
]

FACTOR = 19.0 / 81.0
DECAY = -0.5


def clamp_difficulty(d: float) -> float:
    return max(1.0, min(10.0, d))


def calculate_retrievability(elapsed_days: float, stability: float) -> float:
    if stability <= 0.0:
        return 0.0
    if elapsed_days <= 0.0:
        return 1.0
    return math.pow(1.0 + FACTOR * (elapsed_days / stability), DECAY)


def calculate_interval(stability: float, target_retention: float = 0.90) -> int:
    if stability <= 0.0:
        return 1
    tr = max(0.70, min(0.98, target_retention))
    ivl = (stability / FACTOR) * (math.pow(tr, 1.0 / DECAY) - 1.0)
    return max(1, int(round(ivl)))


def init_stability(grade: int, weights: List[float] = DEFAULT_WEIGHTS) -> float:
    g_idx = max(1, min(4, grade)) - 1
    return max(0.1, weights[g_idx])


def init_difficulty(grade: int, weights: List[float] = DEFAULT_WEIGHTS) -> float:
    # D0(G) = w4 - exp(w5 * (G - 1)) + 1
    val = weights[4] - math.exp(weights[5] * (grade - 1)) + 1.0
    return clamp_difficulty(val)


def next_difficulty(d: float, grade: int, weights: List[float] = DEFAULT_WEIGHTS) -> float:
    # D'(D, G) = w6 * D0(3) + (1 - w6) * (D - w5 * (G - 3))
    d0_good = init_difficulty(3, weights)
    delta = -weights[5] * (grade - 3)
    val = weights[6] * d0_good + (1.0 - weights[6]) * (d + delta)
    return clamp_difficulty(val)


def next_recall_stability(
    s: float, d: float, r: float, grade: int, weights: List[float] = DEFAULT_WEIGHTS
) -> float:
    hard_penalty = weights[15] if grade == 2 else 1.0
    easy_bonus = weights[16] if grade == 4 else 1.0
    # S'(S, D, R, G) = S * (1 + exp(w8) * (11 - D) * S^(-w9) * (exp(w10 * (1 - R)) - 1) * bonus)
    b_term = math.exp(weights[8]) * (11.0 - d) * math.pow(s, -weights[9]) * (math.exp(weights[10] * (1.0 - r)) - 1.0)
    new_s = s * (1.0 + b_term * hard_penalty * easy_bonus)
    return max(0.1, new_s)


def next_forget_stability(
    s: float, d: float, r: float, weights: List[float] = DEFAULT_WEIGHTS
) -> float:
    # S'_lapse = w11 * D^(-w12) * ((S + 1)^w13 - 1) * exp(w14 * (1 - R))
    base = weights[11] * math.pow(d, -weights[12]) * (math.pow(s + 1.0, weights[13]) - 1.0) * math.exp(weights[14] * (1.0 - r))
    return max(0.1, min(s, base))


def step_card_fsrs(
    s: float, d: float, elapsed_days: float, grade: int, weights: List[float] = DEFAULT_WEIGHTS
) -> Tuple[float, float, float]:
    """
    Simulates / steps card forward on a review grade (1=Again, 2=Hard, 3=Good, 4=Easy).
    Returns (new_stability, new_difficulty, retrievability_before_answer).
    """
    if s <= 0.0:
        new_s = init_stability(grade, weights)
        new_d = init_difficulty(grade, weights)
        return new_s, new_d, 1.0

    r = calculate_retrievability(elapsed_days, s)
    new_d = next_difficulty(d, grade, weights)

    if grade == 1:  # Lapse
        new_s = next_forget_stability(s, new_d, r, weights)
    else:  # Recall
        new_s = next_recall_stability(s, new_d, r, grade, weights)

    return new_s, new_d, r


def get_all_intervals(
    s: float, d: float, elapsed_days: float, target_retention: float = 0.90, weights: List[float] = DEFAULT_WEIGHTS
) -> Dict[str, int]:
    """Computes next intervals for all 4 buttons (Again, Hard, Good, Easy) in days."""
    res = {}
    for name, g in [("again", 1), ("hard", 2), ("good", 3), ("easy", 4)]:
        ns, nd, _ = step_card_fsrs(s, d, elapsed_days, g, weights)
        res[name] = calculate_interval(ns, target_retention)
    return res
