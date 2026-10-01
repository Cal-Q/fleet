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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.db import open_dict_db

WORKSPACE_DIR = "/opt/japan"
GOALPOSTS_FILE = os.path.join(WORKSPACE_DIR, "applications", "sunday_goalposts.json")
CAREER_FILE = os.path.join(WORKSPACE_DIR, "applications", "unito_career.json")


def load_json(path: str) -> Dict[str, Any]:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_current_week_goalpost(
    goalposts_data: Dict[str, Any], date_str: str
) -> Dict[str, Any]:
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
    career = load_json(CAREER_FILE)

    current_gp = get_current_week_goalpost(goalposts, target_date_str)
    g_stats = {}
    try:
        conn = open_dict_db(read_only=True)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT level,
                   sum(case when in_anki=1 then 1 else 0 end),
                   sum(case when in_anki=0 then 1 else 0 end),
                   count(*)
            FROM bunpro_grammar_points
            GROUP BY level
            """
        )
        g_stats = {
            r[0]: {"studied": r[1] or 0, "unstudied": r[2] or 0, "total": r[3]}
            for r in cur.fetchall()
        }
        conn.close()
    except Exception:
        pass

    n4_info = g_stats.get("N4", {})
    n3_info = g_stats.get("N3", {})
    studied_n4 = n4_info.get("studied", 0)
    total_n4 = n4_info.get("total", 0)
    unstudied_n4 = n4_info.get("unstudied", 0)
    studied_n3 = n3_info.get("studied", 0)
    total_n3 = n3_info.get("total", 0)

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
    n4_std = report["live_metrics"]["n4_studied"]
    n4_rem = report["live_metrics"]["n4_remaining"]
    n3_std = report["live_metrics"]["n3_studied"]
    print(f"📚 Grammatica Live:  N4: {n4_std} ({n4_rem} residue) | N3: {n3_std}")
    print(f"🎯 Target Settimana: {report['targets']['grammar']}")
    print(f"📝 Target Kanji:     {report['targets']['kanji']}")
    print(f"📖 Target Vocab:     {report['targets']['vocab']}")
    print(f"🏛️ Milestone Admin:  {report['targets']['admin']}")
    gpa = report["live_metrics"]["mext_gpa"]
    cfu = report["live_metrics"]["cfu_area_certified"]
    print(f"⭐ GPA MEXT Live:    {gpa} / 3.00 (CFU d'area: {cfu})")
    print("=" * 72)


if __name__ == "__main__":
    rep = run_weekly_review()
    print_cli_summary(rep)
