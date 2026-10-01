#!/usr/bin/env python3
"""
scripts/anti_heuristic_watchdog.py
Internal watchdog for the agent to detect heuristics, mock preassignments,
and deprecated sm2 references in the active codebase.
Strictly <= 200 lines and <= 100 chars per line invariant.
"""
import os
import re
import sys
from pathlib import Path

TARGET_DIRS = ["core", "api", "static/js/modules", "scripts"]
IGNORE_EXTS = {".pyc", ".png", ".jpg", ".map"}

FORBIDDEN_PATTERNS = [
    (
        r"\bsm2\b",
        "Deprecated SM-2 reference (use authentic Anki scheduler)",
        re.IGNORECASE,
    ),
    (
        r"(?:again_str|hard_str|good_str|easy_str)\s*=\s*[\"']",
        "Hardcoded mock interval preassignment",
        0,
    ),
    (
        r"counts\.learning\s*[-=]",
        "Manual heuristic decrement on learning counter",
        0,
    ),
    (
        r"queue\s*===\s*1.*isLeech|isLeech.*queue\s*===\s*1",
        "Leech heuristic applied to learning cards",
        0,
    ),
]


def scan_file(file_path: Path):
    violations = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        return [f"Could not read {file_path}: {exc}"]

    lines = content.splitlines()
    for line_no, line in enumerate(lines, 1):
        for pattern, desc, flags in FORBIDDEN_PATTERNS:
            if re.search(pattern, line, flags=flags):
                violations.append(
                    f"[{file_path}:{line_no}] {desc}\n  Line: {line.strip()}"
                )
    return violations


def run_watchdog(root_dir: Path):
    total_scanned = 0
    all_violations = []

    for target in TARGET_DIRS:
        target_path = root_dir / target
        if not target_path.exists():
            continue
        if target_path.is_file():
            files = [target_path]
        else:
            files = [
                p
                for p in target_path.rglob("*")
                if p.is_file() and p.suffix not in IGNORE_EXTS
            ]

        for file_path in files:
            if file_path.name == "anti_heuristic_watchdog.py":
                continue
            total_scanned += 1
            v = scan_file(file_path)
            all_violations.extend(v)

    return total_scanned, all_violations


def main():
    root = Path(__file__).resolve().parent.parent
    total, violations = run_watchdog(root)

    print("=" * 60)
    print("ANTI-HEURISTIC & SCHEDULER PURITY WATCHDOG")
    print(f"Scanned {total} active source files across core, api, js, scripts.")
    print("=" * 60)

    if violations:
        print(f"\n❌ ALERT: Found {len(violations)} heuristic violation(s)!\n")
        for v in violations:
            print(f"- {v}\n")
        print("ACTION: Remove heuristics or consult user before proceeding.")
        sys.exit(1)

    print("✅ WATCHDOG CLEAN: Zero heuristics, 0 mock preassignments, 0 SM-2.")
    sys.exit(0)


if __name__ == "__main__":
    main()
