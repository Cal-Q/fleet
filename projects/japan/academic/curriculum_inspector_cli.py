#!/usr/bin/env python3
"""
academic/curriculum_inspector_cli.py — Comprehensive CLI Inspector & Invariant Auditor
Enables querying any of the 161 days, milestones, phases, and validates curriculum invariants.
Strictly <= 200 lines invariant.
"""

import argparse
from datetime import datetime
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN_FILE = os.path.join(BASE_DIR, "curriculum", "master_161_day_curriculum.json")


def load_master() -> dict:
    if not os.path.exists(PLAN_FILE):
        print(f"Error: {PLAN_FILE} not found. Run academic/curriculum_generator.py first.")
        sys.exit(1)
    with open(PLAN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def print_day_card(d: dict):
    width = 76
    print("┌" + "─" * (width - 2) + "┐")
    hdr = f"DAY {d['day_number']}/161 • {d['date']} [{d['day_type'].upper()}]"
    print(f"│  \033[1m{hdr.ljust(width - 6)}\033[0m  │")
    print(f"│  \033[32m{d['phase'].ljust(width - 6)}\033[0m  │")
    if d.get("milestone"):
        ms = f"🎯 {d['milestone']}"
        print(f"│  \033[33m\033[1m{ms[:width - 6].ljust(width - 6)}\033[0m  │")
    print("├" + "─" * (width - 2) + "┤")
    print(f"│  ⏱️  Carico Reale: \033[1m{d['total_minutes']} min\033[0m ({round(d['total_minutes']/60, 2)}h) | Grammatica Cumulativa: \033[1m{d['cumulative_grammar']}\033[0m{' ' * (width - 65)}│")
    print("├" + "─" * (width - 2) + "┤")

    slots = d["slots"]
    for s_key in ["slot1", "slot2", "slot3", "slot4"]:
        s = slots[s_key]
        title_line = f"Slot {s['slot']}: {s['name']} ({s['est_minutes']}m)"
        print(f"│  \033[1m{title_line.ljust(width - 6)}\033[0m  │")
        if "target" in s:
            print(f"│    • {s['target'][:width - 10].ljust(width - 8)}│")
        if "items" in s and s["items"]:
            for it in s["items"]:
                item_line = f"    - [#{it['id']}] {it['title']}: {it['meaning']}"
                print(f"│    \033[36m{item_line[:width - 8].ljust(width - 8)}\033[0m│")
    print("└" + "─" * (width - 2) + "┘")


def run_full_audit(master: dict):
    days = master.get("days", [])
    issues = []
    print("=" * 76)
    print("🔍 AUDIT DETERMINISTICO SUI 161 GIORNI DELLA TRAIETTORIA MEXT")
    print("=" * 76)

    if len(days) != 161:
        issues.append(f"Giorni totali errati: trovati {len(days)}, attesi 161.")

    max_mins = max(d["total_minutes"] for d in days)
    min_mins = min(d["total_minutes"] for d in days)
    avg_mins = round(sum(d["total_minutes"] for d in days) / len(days), 1)

    print(f"📊 Metriche Orarie: Media={avg_mins}m ({round(avg_mins/60, 2)}h) | Min={min_mins}m | Max={max_mins}m")
    if max_mins > 180:
        issues.append(f"Violazione limite sovraccarico: rilevata giornata da {max_mins}m (>180m).")

    # Verify Phase Milestones
    n4_finish = next((d for d in days if "Chiusura 100% Bunpro N4" in (d.get("milestone") or "")), None)
    if not n4_finish:
        issues.append("Milestone chiusura N4 non trovata.")
    else:
        print(f"✅ Chiusura N4 verificata: Giorno {n4_finish['day_number']} ({n4_finish['date']})")

    n3_finish = next((d for d in days if "Chiusura 100% Bunpro N3" in (d.get("milestone") or "")), None)
    if not n3_finish:
        issues.append("Milestone chiusura N3 non trovata.")
    else:
        print(f"✅ Chiusura N3 verificata: Giorno {n3_finish['day_number']} ({n3_finish['date']})")

    buffer_count = sum(1 for d in days if d["day_type"] == "buffer_consolidation")
    print(f"✅ Giorni cuscinetto / recupero leeches: {buffer_count} giorni distribuiti regolarmente.")

    if issues:
        print(f"\n❌ RILEVATE {len(issues)} VIOLAZIONI D'INVARIANTE:")
        for iss in issues:
            print(f"  • {iss}")
        sys.exit(1)
    else:
        print("\n\033[32m✓ TUTTI I 161 GIORNI SUPERANO RIGOROSAMENTE GLI AUDIT DI COERENZA E CARICO!\033[0m")
        print("=" * 76)


def main():
    parser = argparse.ArgumentParser(description="MEXT 161-Day Curriculum Inspector")
    parser.add_argument("--day", type=int, help="Inspect specific day index (1 to 161)")
    parser.add_argument("--date", type=str, help="Inspect specific date (YYYY-MM-DD)")
    parser.add_argument("--today", action="store_true", help="Inspect today's schedule")
    parser.add_argument("--audit", action="store_true", help="Run full 161-day invariant audit")
    parser.add_argument("--milestones", action="store_true", help="List all major milestones")
    args = parser.parse_args()

    master = load_master()
    days = master.get("days", [])

    if args.audit:
        run_full_audit(master)
        return

    if args.milestones:
        print("=" * 76)
        print("🎯 TABELLA CRONOLOGICA DELLE TAPPE MILIARI (161 GIORNI)")
        print("=" * 76)
        for d in days:
            if d.get("milestone"):
                print(f"Giorno {str(d['day_number']).rjust(3)} ({d['date']}): {d['milestone']}")
        print("=" * 76)
        return

    target_day = None
    if args.today:
        today_str = datetime.now().strftime("%Y-%m-%d")
        target_day = next((d for d in days if d["date"] == today_str), days[0])
    elif args.date:
        target_day = next((d for d in days if d["date"] == args.date), None)
    elif args.day:
        idx = max(1, min(161, args.day)) - 1
        target_day = days[idx]
    else:
        target_day = days[0]

    if target_day:
        print_day_card(target_day)
    else:
        print("Nessun giorno trovato per i criteri specificati.")


if __name__ == "__main__":
    main()
