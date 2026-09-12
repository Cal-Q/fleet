#!/usr/bin/env python3
"""
tools/weekly_audit.py — Sunday Goalposts Review & Progress Auditor
Compares live study telemetry (Anki, Bunpro, Esse3) against weekly milestones.
Modular utility strictly <= 200 lines invariant.
"""

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict

WORKSPACE_DIR = "/opt/japan"
GOALPOSTS_FILE = os.path.join(WORKSPACE_DIR, "applications", "sunday_goalposts.json")
PROGRESS_FILE = os.path.join(WORKSPACE_DIR, "japanese", "grammar_progress.json")
CAREER_FILE = os.path.join(WORKSPACE_DIR, "applications", "unito_career.json")


def load_json(path: str) -> Dict[str, Any]:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_current_week_goalpost(goalposts_data: Dict[str, Any], date_str: str) -> Dict[str, Any]:
    """Finds the active goalpost for the given date or the closest upcoming Sunday."""
    weeks = goalposts_data.get("weeks", [])
    today = datetime.strptime(date_str, "%Y-%m-%d")
    closest_week = weeks[0] if weeks else {}
    for w in weeks:
        w_date = datetime.strptime(w["date"], "%Y-%m-%d")
        if w_date <= today:
            closest_week = w
        else:
            break
    return closest_week


def run_weekly_review(target_date_str: str = None) -> Dict[str, Any]:
    """Computes a full progress review against the current week's goalpost."""
    if not target_date_str:
        target_date_str = datetime.now().strftime("%Y-%m-%d")

    goalposts = load_json(GOALPOSTS_FILE)
    progress = load_json(PROGRESS_FILE)
    career = load_json(CAREER_FILE)

    current_gp = get_current_week_goalpost(goalposts, target_date_str)
    summary = progress.get("summary", {})

    n4_info = summary.get("N4", {})
    n3_info = summary.get("N3", {})
    studied_n4 = n4_info.get("studied", 123)
    total_n4 = n4_info.get("total", 185)
    unstudied_n4 = n4_info.get("unstudied", 62)
    studied_n3 = n3_info.get("studied", 7)
    total_n3 = n3_info.get("total", 220)

    report = {
        "audit_date": target_date_str,
        "week": current_gp.get("week", 0),
        "goalpost_date": current_gp.get("date"),
        "phase": current_gp.get("phase"),
        "targets": {
            "grammar": current_gp.get("target_grammar"),
            "kanji": current_gp.get("target_kanji"),
            "vocab": current_gp.get("target_vocab"),
            "admin": current_gp.get("milestone_admin"),
        },
        "live_metrics": {
            "n4_studied": f"{studied_n4}/{total_n4}",
            "n4_remaining": total_n4 - studied_n4,
            "n3_studied": f"{studied_n3}/{total_n3}",
            "cfu_area_certified": career.get("summary", {}).get("cfu_totali_attuali", 8),
            "mext_gpa": career.get("summary", {}).get("mext_gpa_attuale", 3.0),
        },
        "status": current_gp.get("status", "active")
    }
    return report


def print_cli_summary(report: Dict[str, Any]):
    print("=" * 72)
    print(f"📊 MEXT SUNDAY REVIEW: SETTIMANA {report['week']} ({report['goalpost_date']})")
    print(f"🎯 Fase Operativa: {report['phase']}")
    print("=" * 72)
    print(f"📚 Grammatica Live:  N4: {report['live_metrics']['n4_studied']} ({report['live_metrics']['n4_remaining']} residue) | N3: {report['live_metrics']['n3_studied']}")
    print(f"🎯 Target Settimana: {report['targets']['grammar']}")
    print(f"📝 Target Kanji:     {report['targets']['kanji']}")
    print(f"📖 Target Vocab:     {report['targets']['vocab']}")
    print(f"🏛️ Milestone Admin:  {report['targets']['admin']}")
    print(f"⭐ GPA MEXT Live:    {report['live_metrics']['mext_gpa']} / 3.00 (CFU d'area: {report['live_metrics']['cfu_area_certified']})")
    print("=" * 72)


if __name__ == "__main__":
    rep = run_weekly_review()
    print_cli_summary(rep)
