#!/usr/bin/env python3
"""
api/routes/curriculum_routes.py — REST API for MEXT Daily Plan, Trajectory & Master 161 Days
Strictly <= 200 lines invariant.
"""

import json
import os
from fastapi import APIRouter, HTTPException
from engine.daily_curriculum_engine import (
    compute_macro_trajectory,
    get_today_granular_plan,
    audit_routine_invariants,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MASTER_FILE = os.path.join(BASE_DIR, "curriculum", "master_161_day_curriculum.json")

router = APIRouter(prefix="/api/curriculum", tags=["curriculum"])


def load_master_safe() -> dict:
    if os.path.exists(MASTER_FILE):
        try:
            with open(MASTER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


@router.get("/daily-plan")
def get_daily_plan():
    plan = get_today_granular_plan()
    issues = audit_routine_invariants(plan)
    return {
        "success": True,
        "plan": plan,
        "audit_issues": issues,
    }


@router.get("/trajectory")
def get_trajectory():
    traj = compute_macro_trajectory()
    return {
        "success": True,
        "trajectory": traj,
    }


@router.get("/audit")
def get_curriculum_audit():
    plan = get_today_granular_plan()
    issues = audit_routine_invariants(plan)
    return {
        "success": True,
        "has_violations": len(issues) > 0,
        "violations": issues,
    }


@router.get("/master")
def get_master_curriculum():
    data = load_master_safe()
    if not data:
        raise HTTPException(status_code=404, detail="Master curriculum not generated")
    return {
        "success": True,
        "metadata": data.get("metadata", {}),
        "days_count": len(data.get("days", [])),
        "days": [
            {
                "day_number": d["day_number"],
                "date": d["date"],
                "phase": d["phase"],
                "day_type": d["day_type"],
                "milestone": d.get("milestone"),
                "total_minutes": d["total_minutes"],
                "grammar_count": len(d["slots"]["slot2"].get("items", [])),
            }
            for d in data.get("days", [])
        ]
    }


@router.get("/day/{day_identifier}")
def get_curriculum_day(day_identifier: str):
    data = load_master_safe()
    days = data.get("days", [])
    found = None

    if day_identifier.isdigit():
        num = int(day_identifier)
        if 1 <= num <= len(days):
            found = days[num - 1]
    else:
        found = next((d for d in days if d["date"] == day_identifier), None)

    if not found:
        raise HTTPException(status_code=404, detail=f"Day '{day_identifier}' not found in 161-day curriculum")

    return {
        "success": True,
        "day": found,
    }
