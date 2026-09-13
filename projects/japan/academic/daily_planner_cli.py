#!/usr/bin/env python3
"""
academic/daily_planner_cli.py — CLI Inspector for MEXT Daily Trajectory & Prescriptions
Provides fine-grained diagnostic reports and today's exact task list.
Strictly <= 200 lines invariant.
"""

import argparse
import json
import sys
import os

BASE_DIR = "/opt/japan"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from engine.daily_curriculum_engine import (
    compute_macro_trajectory,
    get_today_granular_plan,
    audit_routine_invariants,
)


def render_ascii_box(title: str, lines: list):
    width = 76
    print("┌" + "─" * (width - 2) + "┐")
    print(f"│  \033[1m{title.ljust(width - 6)}\033[0m  │")
    print("├" + "─" * (width - 2) + "┤")
    for line in lines:
        # Strip ANSI for length calculation
        clean_len = len(line.replace("\033[1m", "").replace("\033[0m", "").replace("\033[32m", "").replace("\033[33m", "").replace("\033[36m", "").replace("\033[31m", ""))
        pad = max(0, width - 4 - clean_len)
        print(f"│ {line}{' ' * pad} │")
    print("└" + "─" * (width - 2) + "┘")


def print_daily_plan(plan: dict):
    lines = [
        f"📅 Data Operativa: \033[1m{plan['date']}\033[0m | Fase Attiva: \033[32m{plan['active_phase']}\033[0m",
        f"⏱️  Carico Totale Reale: \033[1m{plan['total_estimated_minutes']} min\033[0m ({plan['total_estimated_hours']} ore nette)",
        "─" * 72,
    ]

    for t in plan["tasks"]:
        slot_hdr = f"\033[1mSlot {t['slot']}: {t['category']}\033[0m ({t['est_minutes']} min)"
        lines.append(slot_hdr)
        lines.append(f"  🎯 {t['title']}")
        if "target" in t:
            lines.append(f"  • {t['target']} [{t.get('live_status', '')}]")
        if "description" in t:
            lines.append(f"  • {t['description']}")
        if "items" in t:
            for it in t["items"]:
                lines.append(f"    - \033[36m[#{it['id']}]\033[0m \033[1m{it['title']}\033[0m: {it['meaning']}")
        lines.append("")

    render_ascii_box("MEXT DAILY PRESCRIPTION • DETTAGLIO GIORNALIERO", lines)


def print_trajectory(traj: dict):
    p1 = traj["phases"]["phase1"]
    p2 = traj["phases"]["phase2"]
    p3 = traj["phases"]["phase3"]

    lines = [
        f"🎯 Obiettivo Finale: Borsa MEXT Japanese Studies ({traj['exam_date']})",
        f"⏳ Giorni Residui Totali: \033[1m{traj['total_days_remaining']} giorni\033[0m",
        "─" * 72,
        f"\033[1m1. {p1['name']}\033[0m {'\033[32m[IN CORSO]\033[0m' if p1['is_active'] else ''}",
        f"   • Punti N4 da studiare: {p1['grammar_remaining']} | Ritmo: {p1['daily_rate']}/die",
        f"   • Durata prevista: {p1['days_required']} giorni | \033[1mData Chiusura N4: {p1['end_date']}\033[0m",
        "",
        f"\033[1m2. {p2['name']}\033[0m {'\033[32m[ATTIVO]\033[0m' if p2['is_active'] else ''}",
        f"   • Punti N3 da studiare: {p2['grammar_remaining']} | Ritmo: {p2['daily_rate']}/die",
        f"   • Finestra: {p2['start_date']} ──> \033[1m{p2['end_date']}\033[0m ({p2['days_required']} giorni)",
        "",
        f"\033[1m3. {p3['name']}\033[0m",
        f"   • Finestra: {p3['start_date']} ──> \033[1m{p3['end_date']}\033[0m ({p3['days_allocated']} giorni)",
        f"   • Focus: Full mock exams 60m (A+B+C) + Simulazione Orale Ambasciata",
    ]

    render_ascii_box("MEXT 3-MACROCYCLE PERIODIZATION • TRAIETTORIA MATEMATICA", lines)


def main():
    parser = argparse.ArgumentParser(description="MEXT Daily Trajectory & Prescriptions")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--trajectory", action="store_true", help="Show trajectory only")
    args = parser.parse_args()

    plan = get_today_granular_plan()
    issues = audit_routine_invariants(plan)

    if args.json:
        print(json.dumps({"plan": plan, "audit_issues": issues}, indent=2, ensure_ascii=False))
        return

    if args.trajectory:
        print_trajectory(plan["trajectory"])
        return

    print_trajectory(plan["trajectory"])
    print()
    print_daily_plan(plan)

    if issues:
        print("\n\033[31m⚠️ INVARIANT VIOLATIONS DETECTED:\033[0m")
        for iss in issues:
            print(f"  [{iss['severity']}] {iss['code']}: {iss['message']}")
    else:
        print("\n\033[32m✓ Nessuna violazione d'invariante: Routine calibrata sui dati reali al 100%.\033[0m")


if __name__ == "__main__":
    main()
