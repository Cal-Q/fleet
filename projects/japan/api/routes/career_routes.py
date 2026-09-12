#!/usr/bin/env python3
"""
Career and Academic Records API Routes
Handles UniTO Esse3 career tracking, GPA simulation, and area credits.
Modular route file strictly <= 200 lines invariant.
"""

import json
import os
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["career"])

WORKSPACE_DIR = "/opt/japan"
CAREER_FILE = os.path.join(WORKSPACE_DIR, "applications", "unito_career.json")


def _calculate_mext_gpa(superate: list) -> float:
    """Calculates official MEXT 3-point GPA from graded exams."""
    total_cfu = 0
    weighted_sum = 0
    for item in superate:
        cfu = item.get("cfu", 0)
        mext_point = item.get("mext_point")
        if mext_point is not None and cfu > 0:
            total_cfu += cfu
            weighted_sum += cfu * mext_point
    if total_cfu == 0:
        return 0.0
    return round(weighted_sum / total_cfu, 2)


@router.get("/api/career")
def get_career():
    """Returns the official Esse3 libretto state, GPA and area credits."""
    if not os.path.exists(CAREER_FILE):
        raise HTTPException(status_code=404, detail="Career file not found.")
    with open(CAREER_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Recalculate dynamic values
    superate = data.get("attivita_superate", [])
    in_corso = data.get("attivita_in_corso_frequentate", [])

    cfu_superati = sum(x.get("cfu", 0) for x in superate)
    cfu_area_superati = sum(x.get("cfu", 0) for x in superate if x.get("is_area"))
    cfu_area_in_corso = sum(x.get("cfu", 0) for x in in_corso if x.get("is_area"))

    data["summary"]["cfu_totali_attuali"] = cfu_superati
    data["summary"]["cfu_area_superati"] = cfu_area_superati
    data["summary"]["cfu_area_in_corso"] = cfu_area_in_corso
    data["summary"]["cfu_area_potenziali_gennaio"] = cfu_area_superati + cfu_area_in_corso
    data["summary"]["mext_gpa_attuale"] = _calculate_mext_gpa(superate)

    return data


@router.get("/api/goalposts")
def get_goalposts():
    """Returns the weekly Sunday goalposts schedule and current week audit."""
    from academic.weekly_audit import run_weekly_review, GOALPOSTS_FILE, load_json
    goalposts = load_json(GOALPOSTS_FILE)
    current_audit = run_weekly_review()
    return {
        "schedule": goalposts,
        "current_review": current_audit
    }


@router.get("/api/universities/preferences")
def get_placement_preferences():
    """Returns the candidate's official 3 placement choices and reserve."""
    pref_file = os.path.join(WORKSPACE_DIR, "applications", "placement_preferences.json")
    if not os.path.exists(pref_file):
        raise HTTPException(status_code=404, detail="Placement preferences not found.")
    with open(pref_file, "r", encoding="utf-8") as f:
        return json.load(f)


