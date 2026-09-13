#!/usr/bin/env python3
"""
engine/monte_carlo_srs.py — Stochastic Monte Carlo Workload & Retention Simulator
Runs multi-trial simulations with lapse jitters and cognitive load variance over 161 days.
Strictly <= 200 lines invariant.
"""

import math
import random
from typing import Any, Dict, List, Tuple


class MonteCarloSRSSimulator:
    def __init__(self, baseline_mature: int = 5052, baseline_rate: float = 24.0):
        self.baseline_mature = baseline_mature
        self.baseline_rate = baseline_rate
        # Base retention intervals with lapse probabilities
        self.intervals = [
            (1, 0.94, 0.06),
            (3, 0.86, 0.14),
            (7, 0.76, 0.18),
            (16, 0.66, 0.20),
            (35, 0.56, 0.22),
            (80, 0.46, 0.25),
            (150, 0.36, 0.28),
        ]

    def run_single_trial(self, daily_new: List[int], noise_level: float = 0.15) -> List[float]:
        num_days = len(daily_new)
        reviews = [max(12.0, random.gauss(self.baseline_rate, self.baseline_rate * noise_level)) for _ in range(num_days)]

        for intro_day, count in enumerate(daily_new):
            if count <= 0:
                continue
            for offset, survival, lapse_rate in self.intervals:
                due_day = intro_day + offset
                if due_day < num_days:
                    # Stochastically vary survival based on card difficulty jitter
                    jittered_survival = max(0.2, min(1.0, random.gauss(survival, noise_level)))
                    reviews[due_day] += count * jittered_survival
                    # Model lapsed cards that resurface 1-2 days later
                    lapsed_day = due_day + random.randint(1, 2)
                    if lapsed_day < num_days:
                        reviews[lapsed_day] += count * lapse_rate * 0.5

        return reviews

    def simulate_trials(self, daily_new: List[int], trials: int = 500) -> Dict[str, Any]:
        num_days = len(daily_new)
        all_trials = [self.run_single_trial(daily_new) for _ in range(trials)]

        mean_per_day = []
        p95_per_day = []
        max_per_day = []

        for d in range(num_days):
            day_vals = [all_trials[t][d] for t in range(trials)]
            day_vals.sort()
            mean_per_day.append(round(sum(day_vals) / trials, 1))
            p95_per_day.append(round(day_vals[int(trials * 0.95)], 1))
            max_per_day.append(round(max(day_vals), 1))

        overall_max_p95 = max(p95_per_day)
        spikes_p95 = sum(1 for v in p95_per_day if v > 75.0)
        overall_mean = sum(mean_per_day) / num_days

        return {
            "trials_count": trials,
            "mean_daily_reviews": round(overall_mean, 1),
            "max_p95_reviews": overall_max_p95,
            "p95_spikes_count": spikes_p95,
            "workload_risk_index": round(spikes_p95 / num_days * 100, 2),
            "daily_p95_curve": p95_per_day,
            "daily_mean_curve": mean_per_day,
        }


if __name__ == "__main__":
    sim = MonteCarloSRSSimulator()
    sample_sched = [12 if (i % 7 < 5) else 0 for i in range(161)]
    res = sim.simulate_trials(sample_sched, trials=200)
    print("Monte Carlo Simulation Results (200 Trials):")
    print(f"  Mean Daily Reviews: {res['mean_daily_reviews']}")
    print(f"  Peak 95th Percentile Reviews: {res['max_p95_reviews']}")
    print(f"  P95 Spikes Count (>75 cards): {res['p95_spikes_count']}")
    print(f"  Workload Risk Index: {res['workload_risk_index']}%")
