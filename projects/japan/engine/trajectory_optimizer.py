#!/usr/bin/env python3
"""
engine/trajectory_optimizer.py — Multi-Epoch Trajectory & Curriculum Schedule Optimizer
Iterates over 161-day candidate plans to balance cognitive load, buffer days, and MEXT readiness.
Strictly <= 200 lines invariant.
"""

from datetime import datetime, timedelta
import os
import sys
from typing import Any, Dict, List, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from engine.curriculum_graph import get_curriculum_stream
from engine.srs_simulator import SRSSimulator

TOTAL_DAYS = 161
START_DATE = "2026-09-13"


def generate_candidate_schedule(
    stream: Dict[str, Any],
    n4_daily_rate: int = 4,
    n3_daily_rate: int = 4,
    buffer_interval: int = 7
) -> List[Dict[str, Any]]:
    n4_queue = list(stream["N4"])
    n3_queue = list(stream["N3"])
    n2_queue = list(stream["N2"])

    start_dt = datetime.strptime(START_DATE, "%Y-%m-%d")
    days = []
    cum_grammar = 0

    for day_idx in range(TOTAL_DAYS):
        day_num = day_idx + 1
        curr_date = start_dt + timedelta(days=day_idx)
        date_str = curr_date.strftime("%Y-%m-%d")
        is_buffer = (day_num % buffer_interval == 0)

        # Determine phase
        if n4_queue:
            phase = "Fase 1: Chiusura N4 & Blindatura Parte A"
            phase_num = 1
        elif n3_queue:
            phase = "Fase 2: Padronanza N3 & Drill Parte B"
            phase_num = 2
        else:
            phase = "Fase 3: Full Past Papers & Simulazione Orale"
            phase_num = 3

        # Allocate grammar batch
        grammar_batch = []
        if not is_buffer and day_num < 152:  # Final 9 days are tapering
            if n4_queue:
                take = min(n4_daily_rate, len(n4_queue))
                grammar_batch = [n4_queue.pop(0) for _ in range(take)]
            elif n3_queue:
                take = min(n3_daily_rate, len(n3_queue))
                grammar_batch = [n3_queue.pop(0) for _ in range(take)]
            elif n2_queue and phase_num == 2:
                take = min(2, len(n2_queue))
                grammar_batch = [n2_queue.pop(0) for _ in range(take)]

        cum_grammar += len(grammar_batch)

        # Determine day type and tasks
        day_type = "buffer_consolidation" if is_buffer else ("tapering" if day_num >= 152 else "study")
        days.append({
            "day_number": day_num,
            "date": date_str,
            "phase": phase,
            "phase_num": phase_num,
            "day_type": day_type,
            "grammar_points": grammar_batch,
            "grammar_count": len(grammar_batch),
            "cumulative_grammar": cum_grammar,
            "new_vocab_cards": len(grammar_batch) * 3 if day_type == "study" else 0,
        })

    return days


def evaluate_schedule_fitness(days: List[Dict[str, Any]]) -> Tuple[float, Dict[str, Any]]:
    score = 1000.0
    metrics = {}

    # Checkpoint 1: N4 Closure Date
    n4_finish_day = next((d["day_number"] for d in days if d["phase_num"] > 1), None)
    metrics["n4_finish_day"] = n4_finish_day or TOTAL_DAYS
    if n4_finish_day and n4_finish_day <= 14:
        score += 200.0
    else:
        score -= (metrics["n4_finish_day"] - 14) * 30.0

    # Checkpoint 2: N3 Closure Date
    n3_finish_day = next((d["day_number"] for d in days if d["phase_num"] > 2), None)
    metrics["n3_finish_day"] = n3_finish_day or TOTAL_DAYS
    if n3_finish_day and n3_finish_day <= 80:
        score += 200.0
    else:
        score -= (metrics["n3_finish_day"] - 80) * 15.0

    # Checkpoint 3: SRS Simulation & Spikes
    new_cards = [d["new_vocab_cards"] for d in days]
    sim = SRSSimulator()
    srs_res = sim.simulate_trajectory(new_cards)
    srs_metrics = sim.compute_workload_metrics(srs_res)
    metrics["srs_spikes"] = srs_metrics["total_review_spikes"]
    metrics["avg_daily_minutes"] = srs_metrics["avg_daily_minutes"]
    score -= srs_metrics["total_review_spikes"] * 10.0

    # Attach SRS results back into day records
    for i, d in enumerate(days):
        d["srs_data"] = srs_res[i]

    return max(0.0, score), metrics


def optimize_curriculum(epochs: int = 25) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    stream = get_curriculum_stream()
    best_score = -1.0
    best_schedule = []
    best_metrics = {}

    candidates = [
        (4, 4, 7),
        (4, 4, 6),
        (5, 4, 7),
        (4, 3, 7),
        (3, 4, 7),
        (4, 4, 8),
        (4, 5, 7),
    ]

    for epoch in range(epochs):
        params = candidates[epoch % len(candidates)]
        sched = generate_candidate_schedule(stream, *params)
        score, met = evaluate_schedule_fitness(sched)
        if score > best_score:
            best_score = score
            best_schedule = sched
            best_metrics = met
            best_metrics["best_params"] = {
                "n4_rate": params[0],
                "n3_rate": params[1],
                "buffer_interval": params[2],
            }

    best_metrics["fitness_score"] = round(best_score, 2)
    return best_schedule, best_metrics


if __name__ == "__main__":
    sched, met = optimize_curriculum(epochs=15)
    print("Optimization Complete:")
    print(f"  Fitness Score: {met.get('fitness_score')}")
    print(f"  N4 Finish Day: Day {met.get('n4_finish_day')} ({sched[met.get('n4_finish_day') - 1]['date']})")
    print(f"  N3 Finish Day: Day {met.get('n3_finish_day')} ({sched[met.get('n3_finish_day') - 1]['date']})")
    print(f"  SRS Spikes: {met.get('srs_spikes')}")
    print(f"  Best Params: {met.get('best_params')}")
