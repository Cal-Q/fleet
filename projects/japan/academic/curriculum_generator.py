#!/usr/bin/env python3
"""
academic/curriculum_generator.py — Master 161-Day MEXT Curriculum Synthesizer
Enriches optimized trajectory with exact daily slot tasks and writes persistent JSON.
Strictly <= 200 lines invariant.
"""

import json
import os
import sys
from typing import Any, Dict, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from engine.trajectory_optimizer import optimize_curriculum

OUTPUT_FILE = os.path.join(BASE_DIR, "curriculum", "master_161_day_curriculum.json")


def build_slot_tasks(day: Dict[str, Any]) -> Dict[str, Any]:
    phase_num = day["phase_num"]
    is_buffer = (day["day_type"] == "buffer_consolidation")
    is_tapering = (day["day_type"] == "tapering")
    pts = day["grammar_points"]
    srs = day.get("srs_data", {})

    # Slot 1: Anki SRS
    slot1_mins = 35 if is_buffer else (25 if is_tapering else 40)
    slot1 = {
        "slot": 1,
        "name": "Ripasso SRS Anki (Kurogane)",
        "est_minutes": slot1_mins,
        "target": "Zero arretrati sulle 5.052 mature Anki",
        "projected_reps": srs.get("total_reps", 45),
        "is_buffer_mode": is_buffer
    }

    # Slot 2: Grammar / Text
    if is_buffer:
        slot2 = {
            "slot": 2,
            "name": "Consolidamento Settimanale",
            "est_minutes": 30,
            "target": "Revisione punti deboli e schede leech della settimana",
            "items": []
        }
    elif is_tapering:
        slot2 = {
            "slot": 2,
            "name": "Rifinitura & Lettura Calma",
            "est_minutes": 25,
            "target": "Rilettura schede riassuntive e formule fisse senza stress",
            "items": []
        }
    elif phase_num == 1:
        slot2 = {
            "slot": 2,
            "name": f"Sprint Bunpro N4 ({len(pts)} punti)",
            "est_minutes": 45,
            "target": f"Studio intensivo di {len(pts)} punti N4",
            "items": [{"id": p["id"], "title": p["title"], "meaning": p["meaning"], "url": p.get("url", ""), "examples": p.get("examples", [])} for p in pts]
        }
    elif phase_num == 2:
        slot2 = {
            "slot": 2,
            "name": f"Core Bunpro N3 ({len(pts)} punti)",
            "est_minutes": 45,
            "target": f"Studio intensivo di {len(pts)} punti N3",
            "items": [{"id": p["id"], "title": p["title"], "meaning": p["meaning"], "url": p.get("url", ""), "examples": p.get("examples", [])} for p in pts]
        }
    else:
        slot2 = {
            "slot": 2,
            "name": "Skimming Accademico & Comprensione Testi",
            "est_minutes": 40,
            "target": "Lettura veloce articoli e saggi culturali livello N2/N1",
            "items": []
        }

    # Slot 3: Verbi / Sintassi / Orale
    if is_buffer:
        slot3 = {"slot": 3, "name": "Riposo Cognitivo & Vocabolario Passivo", "est_minutes": 15, "target": "Ascolto passivo podcast / anime"}
    elif phase_num == 1:
        slot3 = {"slot": 3, "name": "Frasi Esempio & 12 Verbi Keigo", "est_minutes": 25, "target": "Lettura frasi Bunpro odierne + flashcard 12 verbi irregolari"}
    elif phase_num == 2:
        slot3 = {"slot": 3, "name": "Verbi Composti N2 & Forme Fisse", "est_minutes": 25, "target": "Drill coppie verbali N2 e schemi di giunzione sintattica"}
    else:
        slot3 = {"slot": 3, "name": "Simulazione Colloquio Orale Ambasciata", "est_minutes": 35, "target": "Shadowing risposte modello, studio plan sociologia e UniTO"}

    # Slot 4: Exam Drill
    if is_buffer:
        slot4 = {"slot": 4, "name": "Revisione Errori & Note Prove", "est_minutes": 20, "target": "Analisi approfondita dei commenti e dei distrattori"}
    elif is_tapering:
        slot4 = {"slot": 4, "name": "Warmup Leggero (5-6 quesiti)", "est_minutes": 15, "target": "Mantenimento confidenza senza affaticamento"}
    elif phase_num == 1:
        slot4 = {"slot": 4, "name": "Drill Mirato Parte A (10-12 Qs)", "est_minutes": 15, "target": "Target 95% su particelle e kanji elementari"}
    elif phase_num == 2:
        slot4 = {"slot": 4, "name": "Drill Selettivo Parte B (12-15 Qs)", "est_minutes": 25, "target": "Chirurgico su connettori e composti di Parte B"}
    else:
        slot4 = {"slot": 4, "name": "Full Mock Exam Cronometrato (60m)", "est_minutes": 55, "target": "Simulazione integrale A+B+C con gestione del tempo"}

    total_mins = slot1["est_minutes"] + slot2["est_minutes"] + slot3["est_minutes"] + slot4["est_minutes"]
    return {"slot1": slot1, "slot2": slot2, "slot3": slot3, "slot4": slot4, "total_minutes": total_mins}


def attach_milestones(days: List[Dict[str, Any]]):
    milestone_map = {
        1: "🚀 KICKOFF PIANO 161 GIORNI: Inizio Chiusura N4 & Blindatura Parte A",
        14: "🎉 TRAGUARDO FASE 1: Chiusura 100% Bunpro N4 (185/185)",
        15: "🏁 INIZIO FASE 2: Sprint N3 Core Grammar & Verbi Composti N2",
        45: "📈 MILESTONE N3: Raggiunto 50% del programma Bunpro N3",
        79: "🏆 TRAGUARDO FASE 2: Chiusura 100% Bunpro N3 (220/220)",
        80: "⚔️ INIZIO FASE 3: Full Past Papers Integrali & Simulazione Orale",
        120: "🎯 FULL MOCK EXAM CRONOMETRATO: Prova Generale Past Paper 2017",
        152: "🧘 INIZIO TAPERING: Consolidamento finale, riduzione carico e riposo",
        161: "🇯🇵 GIORNO DELL'ESAME MEXT (Ambasciata del Giappone a Roma)"
    }
    for d in days:
        d["milestone"] = milestone_map.get(d["day_number"], None)


def generate_and_save_curriculum(epochs: int = 25) -> Dict[str, Any]:
    raw_days, metrics = optimize_curriculum(epochs=epochs)
    attach_milestones(raw_days)

    enriched_days = []
    for d in raw_days:
        tasks = build_slot_tasks(d)
        enriched_days.append({
            "day_number": d["day_number"],
            "date": d["date"],
            "phase": d["phase"],
            "phase_num": d["phase_num"],
            "day_type": d["day_type"],
            "milestone": d["milestone"],
            "slots": tasks,
            "total_minutes": tasks["total_minutes"],
            "cumulative_grammar": d["cumulative_grammar"],
            "srs_summary": {
                "reviews_due": d.get("srs_data", {}).get("reviews_due", 30),
                "total_reps": d.get("srs_data", {}).get("total_reps", 45),
            }
        })

    master = {
        "metadata": {
            "title": "MEXT Japanese Studies FY2027 — 161-Day Master Deterministic Curriculum",
            "start_date": raw_days[0]["date"],
            "end_date": raw_days[-1]["date"],
            "total_days": len(raw_days),
            "generated_at": os.popen("date -u +%Y-%m-%dT%H:%M:%SZ").read().strip(),
            "metrics": metrics
        },
        "days": enriched_days
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(master, f, ensure_ascii=False, indent=2)

    return master


if __name__ == "__main__":
    res = generate_and_save_curriculum(epochs=25)
    print(f"Master Curriculum saved to {OUTPUT_FILE}")
    print(f"Total Days: {res['metadata']['total_days']}")
    print(f"Start: {res['metadata']['start_date']} -> End: {res['metadata']['end_date']}")
    print(f"Sample Day 1: {res['days'][0]['slots']['total_minutes']} min, milestone: {res['days'][0]['milestone']}")
    print(f"Sample Day 14: milestone: {res['days'][13]['milestone']}")
    print(f"Sample Day 161: milestone: {res['days'][160]['milestone']}")
