#!/usr/bin/env python3
"""
scripts/expand_pools.py — Expands Drill Pools A, B, and C with new verified questions.
Strictly <= 200 lines invariant.
"""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from new_questions_a1 import QUESTIONS_A1
from new_questions_a2 import QUESTIONS_A2
from new_questions_b1 import QUESTIONS_B1
from new_questions_b2 import QUESTIONS_B2
from new_questions_c import QUESTIONS_C

EXAMS_DIR = os.path.join(BASE_DIR, "exams")


def append_unique(file_path: str, new_items: list) -> int:
    with open(file_path, "r", encoding="utf-8") as f:
        existing = json.load(f)
    existing_ids = {q["id"] for q in existing}
    added = 0
    for q in new_items:
        if q["id"] not in existing_ids:
            existing.append(q)
            existing_ids.add(q["id"])
            added += 1
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    return len(existing)


def run_expansion():
    print("[*] Expanding MEXT Drill Pools...")
    tot_a = append_unique(
        os.path.join(EXAMS_DIR, "drill_pool_part_a.json"),
        QUESTIONS_A1 + QUESTIONS_A2
    )
    print(f" [+] Part A Pool expanded: total {tot_a} questions")

    tot_b = append_unique(
        os.path.join(EXAMS_DIR, "drill_pool_part_b.json"),
        QUESTIONS_B1 + QUESTIONS_B2
    )
    print(f" [+] Part B Pool expanded: total {tot_b} questions")

    tot_c = append_unique(
        os.path.join(EXAMS_DIR, "drill_pool_part_c.json"),
        QUESTIONS_C
    )
    print(f" [+] Part C Pool expanded: total {tot_c} questions")
    print(f"[🎉] Total questions across all 3 pools: {tot_a + tot_b + tot_c}!")


if __name__ == "__main__":
    run_expansion()
