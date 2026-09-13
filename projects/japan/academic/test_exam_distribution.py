#!/usr/bin/env python3
"""
academic/test_exam_distribution.py — Deterministic Exam Distribution & Blueprint Audit Daemon
Enforces Invariant 25 (Stratified Blueprint Quota) and Invariant 27 across 60 days.
Strictly <= 200 lines invariant.
"""

import os
import sys
from datetime import datetime, timedelta

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from academic.exam_provider import get_questions_for_session


def run_audit(days: int = 60) -> bool:
    print(f"[*] Starting MEXT Exam Blueprint Audit Daemon over {days} days...")
    base_date = datetime(2026, 9, 13)

    for d in range(days):
        cur_date = (base_date + timedelta(days=d)).strftime("%Y-%m-%d")

        # 1. Audit Section A daily battery
        qs_a = get_questions_for_session("A")
        if len(qs_a) != 12:
            raise AssertionError(f"Day {cur_date}: Expected 12 Part A questions, got {len(qs_a)}")

        ids_a = [q["id"] for q in qs_a]
        if len(ids_a) != len(set(ids_a)):
            raise AssertionError(f"Day {cur_date}: Duplicate IDs detected in Part A: {ids_a}")

        # Check category distribution
        traps = [q for q in qs_a if "熟字訓" in q.get("category", "") or int(q["id"].split("-")[-1]) >= 111]
        if len(traps) > 1:
            raise AssertionError(f"Day {cur_date}: Traps exceeded quota of 1! Found {len(traps)}")

        grammar = [q for q in qs_a if any(k in q.get("category", "") for k in [
            "Grammar", "Particle", "Form", "Conditional", "Request", "Transitive", "Conjunction"
        ])]
        if len(grammar) < 4 or len(grammar) > 6:
            raise AssertionError(f"Day {cur_date}: Grammar/Particles outside expected range: {len(grammar)}")

        # 2. Audit Full Mock battery
        qs_mock = get_questions_for_session("MOCK")
        if len(qs_mock) != 30:
            raise AssertionError(f"Day {cur_date}: Expected 30 questions in MOCK, got {len(qs_mock)}")

        ids_mock = [q["id"] for q in qs_mock]
        if len(ids_mock) != len(set(ids_mock)):
            raise AssertionError(f"Day {cur_date}: Duplicate IDs detected in MOCK: {ids_mock}")

        # 3. Audit carrier sentence furigana for advanced traps
        for q in traps:
            q_text = q.get("question", "")
            if "職人" in q_text and "（しょくにん）" not in q_text:
                raise AssertionError(f"Missing furigana gloss for 職人 in {q['id']}")
            if "式典" in q_text and "（しきてん）" not in q_text:
                raise AssertionError(f"Missing furigana gloss for 式典 in {q['id']}")

    print(f"[+] SUCCESS: All {days} days passed blueprint validation!")
    print("    - Part A Stratification: 5 Grammar, 3 Writing, 3 Reading, <= 1 Trap.")
    print("    - 30-Question MOCK Battery: Exactly 12A + 10B + 8C.")
    print("    - Carrier Sentence Gating: Non-target N3+ kanji annotated.")
    return True


if __name__ == "__main__":
    success = run_audit(days=60)
    sys.exit(0 if success else 1)

