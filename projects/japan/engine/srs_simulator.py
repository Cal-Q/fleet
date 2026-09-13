#!/usr/bin/env python3
"""
engine/srs_simulator.py — Mathematical SRS Review & Workload Simulator
Models Spaced Repetition (SM-2 / half-life decay) over a 161-day trajectory.
Strictly <= 200 lines invariant.
"""

from typing import Dict, List


class SRSSimulator:
    def __init__(self, baseline_mature: int = 5052, baseline_reviews_per_day: float = 24.0):
        self.baseline_mature = baseline_mature
        self.baseline_reviews = baseline_reviews_per_day
        # Retention decay schedule: (offset_days, survival_probability)
        self.interval_curve = [
            (1, 0.95),
            (3, 0.85),
            (7, 0.75),
            (16, 0.65),
            (35, 0.55),
            (80, 0.45),
            (150, 0.35),
        ]

    def simulate_trajectory(self, daily_new_cards: List[int]) -> List[Dict[str, float]]:
        """Simulates review volume day-by-day given the list of new cards added each day."""
        num_days = len(daily_new_cards)
        daily_reviews = [self.baseline_reviews for _ in range(num_days)]

        for introduce_day, new_count in enumerate(daily_new_cards):
            if new_count <= 0:
                continue
            for offset, survival_rate in self.interval_curve:
                due_day = introduce_day + offset
                if due_day < num_days:
                    daily_reviews[due_day] += new_count * survival_rate

        results = []
        for day_idx in range(num_days):
            new_added = daily_new_cards[day_idx]
            rev_due = daily_reviews[day_idx]
            total_cards = rev_due + new_added
            # 1 card takes approx 12-15 seconds (review + reflection) -> ~4 cards per min
            est_minutes = round(total_cards / 4.2, 1)

            results.append({
                "day_index": day_idx + 1,
                "new_cards": new_added,
                "reviews_due": round(rev_due, 1),
                "total_reps": round(total_cards, 1),
                "est_minutes": max(15.0, est_minutes),
                "is_review_spike": total_cards > 75.0,
            })

        return results

    def compute_workload_metrics(self, simulated_days: List[Dict[str, float]]) -> Dict[str, float]:
        reps = [d["total_reps"] for d in simulated_days]
        minutes = [d["est_minutes"] for d in simulated_days]
        spikes = sum(1 for d in simulated_days if d["is_review_spike"])

        return {
            "avg_daily_reps": round(sum(reps) / len(reps), 1),
            "max_daily_reps": round(max(reps), 1),
            "min_daily_reps": round(min(reps), 1),
            "avg_daily_minutes": round(sum(minutes) / len(minutes), 1),
            "max_daily_minutes": round(max(minutes), 1),
            "total_review_spikes": spikes,
            "workload_stability_score": round(max(0.0, 100.0 - (spikes * 2.5)), 1)
        }


if __name__ == "__main__":
    sim = SRSSimulator()
    # Test a simple 161-day schedule with 12 new cards/day on weekdays, 0 on weekends
    test_cards = [12 if (i % 7 < 5) else 0 for i in range(161)]
    res = sim.simulate_trajectory(test_cards)
    metrics = sim.compute_workload_metrics(res)
    print("SRS Simulation Metrics for 161 Days:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")
    print(f"Sample Day 1: {res[0]}")
    print(f"Sample Day 30: {res[29]}")
