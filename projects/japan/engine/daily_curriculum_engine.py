#!/usr/bin/env python3
"""
engine/daily_curriculum_engine.py — MEXT Fine-Grained Trajectory & Daily Prescriptions
Derives exact daily tasks, realistic time budgets, and milestone dates from live ground truth.
Strictly <= 200 lines invariant.
"""

from datetime import datetime, timedelta
import json
import os
from typing import Any, Dict, List

BASE_DIR = "/opt/japan"
GRAMMAR_FILE = os.path.join(BASE_DIR, "japanese", "grammar_progress.json")
BUNKI_FILE = os.path.join(BASE_DIR, "japanese", "bunki_profile.json")
EXAMS_FILE = os.path.join(BASE_DIR, "exams", "exam_database.json")
LOG_FILE = os.path.join(BASE_DIR, "exams", "practice_log.jsonl")

EXAM_TARGET_DATE = "2027-02-20"


def load_json_safe(path: str, default: Any = None) -> Any:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def compute_macro_trajectory(today_str: str = None) -> Dict[str, Any]:
    if not today_str:
        today_str = datetime.now().strftime("%Y-%m-%d")
    today = datetime.strptime(today_str, "%Y-%m-%d")
    target = datetime.strptime(EXAM_TARGET_DATE, "%Y-%m-%d")
    days_left = max(1, (target - today).days)

    gp = load_json_safe(GRAMMAR_FILE, {})
    unstudied = gp.get("unstudied_by_level", {})
    n4_unstudied = len(unstudied.get("N4", []))
    n3_unstudied = len(unstudied.get("N3", []))
    n2_unstudied = len(unstudied.get("N2", []))

    # Phase 1: N4 Closure (4 points/day)
    n4_days = max(1, (n4_unstudied + 3) // 4)
    phase1_end = today + timedelta(days=n4_days)

    # Phase 2: N3 Mastery & Compounds (3.5 points/day)
    n3_days = max(1, int((n3_unstudied / 3.5) + 0.99))
    phase2_end = phase1_end + timedelta(days=n3_days)

    # Phase 3: Past Papers & Oral Simulation
    phase3_days = max(1, (target - phase2_end).days)

    return {
        "today": today_str,
        "exam_date": EXAM_TARGET_DATE,
        "total_days_remaining": days_left,
        "phases": {
            "phase1": {
                "name": "Fase 1: Chiusura N4 & Blindatura Parte A",
                "grammar_remaining": n4_unstudied,
                "daily_rate": 4.0,
                "days_required": n4_days,
                "end_date": phase1_end.strftime("%Y-%m-%d"),
                "is_active": n4_unstudied > 0
            },
            "phase2": {
                "name": "Fase 2: Padronanza N3 & Drill Parte B",
                "grammar_remaining": n3_unstudied,
                "daily_rate": 3.5,
                "days_required": n3_days,
                "start_date": phase1_end.strftime("%Y-%m-%d"),
                "end_date": phase2_end.strftime("%Y-%m-%d"),
                "is_active": n4_unstudied == 0 and n3_unstudied > 0
            },
            "phase3": {
                "name": "Fase 3: Full Past Papers & Simulazione Orale",
                "days_allocated": phase3_days,
                "start_date": phase2_end.strftime("%Y-%m-%d"),
                "end_date": EXAM_TARGET_DATE,
                "is_active": n4_unstudied == 0 and n3_unstudied == 0
            }
        }
    }


def get_today_granular_plan(today_str: str = None) -> Dict[str, Any]:
    traj = compute_macro_trajectory(today_str)
    gp = load_json_safe(GRAMMAR_FILE, {})
    bunki = load_json_safe(BUNKI_FILE, {})

    unstudied_n4 = gp.get("unstudied_by_level", {}).get("N4", [])
    unstudied_n3 = gp.get("unstudied_by_level", {}).get("N3", [])

    if unstudied_n4:
        active_points = unstudied_n4[:4]
        current_focus = "N4 Closure"
        exam_section = "A"
        exam_title = "Parte A (初級 - Particelle e Kanji)"
        exam_time_min = 15
        interview_mode = "keigo_cards_only"
    elif unstudied_n3:
        active_points = unstudied_n3[:4]
        current_focus = "N3 Core"
        exam_section = "B"
        exam_title = "Parte B (中級 - Connettori e Composti)"
        exam_time_min = 25
        interview_mode = "keigo_compounds"
    else:
        active_points = []
        current_focus = "Full Simulation"
        exam_section = "ALL"
        exam_title = "Simulazione Integrale MEXT (A+B+C)"
        exam_time_min = 60
        interview_mode = "full_oral_defense"

    tasks = [
        {
            "slot": 1,
            "category": "SRS Anki (Kurogane)",
            "title": "Mantenimento Carte Mature",
            "est_minutes": 40,
            "target": "Zero arretrati sulle 5.052 carte mature (Anki).",
            "live_status": f"{bunki.get('mature_cards', 5052)} mature attive"
        },
        {
            "slot": 2,
            "category": f"Grammatica Bunpro ({current_focus})",
            "title": f"Studio di {len(active_points)} Nuovi Punti Grammaticali",
            "est_minutes": 45,
            "items": [
                {
                    "id": p["id"],
                    "title": p["title"],
                    "meaning": p["meaning"],
                    "url": p.get("url", f"https://bunpro.jp/grammar_points/{p['id']}")
                }
                for p in active_points
            ]
        },
        {
            "slot": 3,
            "category": "Frasi & Verbi Fondamentali",
            "title": "Consolidamento Sintassi & 12 Verbi Keigo",
            "est_minutes": 25,
            "mode": interview_mode,
            "description": (
                "Lettura attiva frasi Bunpro per i punti odierni + 12 coppie irregolari Keigo come carte lessicali. "
                "NESSUNA simulazione orale complessa in questa fase."
            )
        },
        {
            "slot": 4,
            "category": "Drill Test MEXT",
            "title": f"Verifica Mirata su {exam_title}",
            "est_minutes": exam_time_min,
            "section": exam_section,
            "count": 12 if exam_section == "A" else 15,
            "description": (
                f"Risoluzione concentrata di 10-12 quesiti di Sezione {exam_section}. "
                "Annotazione immediata dei dubbi e verifica attiva delle spiegazioni."
            )
        }
    ]

    total_min = sum(t["est_minutes"] for t in tasks)

    return {
        "date": traj["today"],
        "active_phase": "Fase 1" if unstudied_n4 else ("Fase 2" if unstudied_n3 else "Fase 3"),
        "total_estimated_minutes": total_min,
        "total_estimated_hours": round(total_min / 60, 2),
        "trajectory": traj,
        "tasks": tasks
    }


def audit_routine_invariants(plan: Dict[str, Any]) -> List[Dict[str, str]]:
    issues = []
    task4 = next((t for t in plan["tasks"] if t["slot"] == 4), None)
    if task4 and task4["section"] == "A" and task4["est_minutes"] > 25:
        issues.append({
            "severity": "ERROR",
            "code": "OVERBUDGET_PART_A",
            "message": f"Parte A ha solo 10-12 quesiti: {task4['est_minutes']}m è sovradimensionato (max 20m)."
        })

    task3 = next((t for t in plan["tasks"] if t["slot"] == 3), None)
    if plan["active_phase"] == "Fase 1" and task3 and task3["mode"] != "keigo_cards_only":
        issues.append({
            "severity": "ERROR",
            "code": "PREMATURE_ORAL_INTERVIEW",
            "message": "Simulazione orale diplomatica prematura prima del completamento di N4."
        })

    return issues
