#!/usr/bin/env python3
"""
tools/exam_drill.py — MEXT Japanese Studies CLI Exam Practice & Telemetry Engine
Strictly <= 200 lines invariant.
"""

import argparse
import json
import os
import sys
import time

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from academic.exam_analytics import get_analytics, record_session

DB_PATH = os.path.join(WORKSPACE_ROOT, "exams", "exam_database.json")


def load_database():
    if not os.path.exists(DB_PATH):
        print(f"Errore: database non trovato in {DB_PATH}")
        sys.exit(1)
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def run_drill(questions, timed=False, max_minutes=100):
    if not questions:
        print("Nessuna domanda trovata per i criteri specificati.")
        return

    print("=" * 72)
    print(f"🎯 MEXT JAPANESE WRITTEN EXAMINATION DRILL — {len(questions)} DOMANDE")
    if timed:
        print(f"⏱️ Tempo massimo della sessione: {max_minutes} minuti")
    print("Seleziona [A, B, C, D] o [Q] per uscire.")
    print("=" * 72)

    score = 0
    total = len(questions)
    results_by_section = {"A": {"correct": 0, "total": 0}, "B": {"correct": 0, "total": 0}, "C": {"correct": 0, "total": 0}}
    results_by_category = {}
    details = []
    start_time = time.time()

    for i, q in enumerate(questions, 1):
        sec = q.get("section", "A")
        cat = q.get("category", "General")
        results_by_section[sec]["total"] += 1
        if cat not in results_by_category:
            results_by_category[cat] = {"correct": 0, "total": 0}
        results_by_category[cat]["total"] += 1

        print(f"\n[Q {i}/{total}] • SEZIONE {sec} ({q.get('level', '')}) — {cat}")
        print("-" * 72)
        print(q["question"])
        print()
        for opt_key in ["A", "B", "C", "D"]:
            if opt_key in q.get("options", {}):
                print(f"  {opt_key}. {q['options'][opt_key]}")

        while True:
            try:
                ans = input("\n👉 La tua risposta [A/B/C/D]: ").strip().upper()
            except (EOFError, KeyboardInterrupt):
                print("\nSessione interrotta.")
                return

            if ans in ["A", "B", "C", "D", "Q"]:
                break
            print("Risposta non valida. Inserisci A, B, C, D oppure Q.")

        if ans == "Q":
            print("Sessione terminata anticipatamente.")
            break

        correct = q.get("answer", "").upper()
        is_correct = (ans == correct)
        if is_correct:
            print("✅ CORRETTO!")
            score += 1
            results_by_section[sec]["correct"] += 1
            results_by_category[cat]["correct"] += 1
        else:
            print(f"❌ SBAGLIATO. Risposta corretta: {correct}")

        print(f"💡 Spiegazione: {q.get('explanation', '')}")

        details.append({
            "id": q.get("id"),
            "question": q.get("question"),
            "category": cat,
            "level": q.get("level", ""),
            "user_answer": ans,
            "correct_answer": correct,
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
            "section": sec
        })

    elapsed_sec = int(time.time() - start_time)
    elapsed_min = elapsed_sec // 60
    rem_sec = elapsed_sec % 60

    print("\n" + "=" * 72)
    print("📊 RIEPILOGO RISULTATI SESSIONE")
    print(f"Punteggio Totale: {score}/{total} ({(score / total * 100) if total > 0 else 0:.1f}%)")
    print(f"Tempo impiegato: {elapsed_min}m {rem_sec}s")
    print("-" * 72)
    for sec_name, data in results_by_section.items():
        if data["total"] > 0:
            pct = (data["correct"] / data["total"]) * 100
            label = {"A": "Part A (初級 ~ N4/N3)", "B": "Part B (中級 ~ N2)", "C": "Part C (上級 ~ N1)"}.get(sec_name, sec_name)
            print(f"  • {label}: {data['correct']}/{data['total']} ({pct:.1f}%)")
    print("=" * 72)

    # Persist session to analytics
    record_session(
        score=score,
        total=len(details),
        time_spent_seconds=elapsed_sec,
        section_breakdown=results_by_section,
        category_breakdown=results_by_category,
        details=details,
        mode="cli_drill"
    )
    print("💾 Sessione salvata nella telemetria analitica (exams/practice_log.jsonl).")


def show_statistics():
    data = get_analytics()
    if data["total_sessions"] == 0:
        print("Nessuna sessione registrata finora. Avvia il drill con: python3 tools/exam_drill.py")
        return

    print("=" * 72)
    print("📈 REPORT TELEMETRIA & VALUTAZIONE METODO MEXT")
    print(f"Sessioni completate: {data['total_sessions']} | Quesiti totali: {data['total_questions']}")
    print(f"Tempo netto di studio: {data['total_time_minutes']} min | Pacing medio: {data['avg_seconds_per_question']}s/quesito")
    print(f"Accuratezza complessiva: {data['overall_accuracy']}%")
    print("-" * 72)

    print("📊 Accuratezza per Sezione:")
    for sec, sdata in data.get("section_accuracy", {}).items():
        if sdata.get("total", 0) > 0:
            print(f"  • Sezione {sec}: {sdata['correct']}/{sdata['total']} ({sdata['percentage']}%)")

    print("\n📚 Mappa Competenze per Categoria:")
    for cat, cdata in sorted(data.get("category_accuracy", {}).items(), key=lambda x: x[1]["percentage"], reverse=True):
        print(f"  • {cat[:28]:<28}: {cdata['percentage']:>5.1f}% ({cdata['correct']}/{cdata['total']})")

    if data.get("weaknesses"):
        print("\n⚠️ Aree Critiche da Consolidare (<65%):")
        for w in data["weaknesses"]:
            print(f"  - {w['category']}: {w['percentage']}% ({w['total']} tentativi)")

    if data.get("strengths"):
        print("\n✅ Punti di Forza (≥80%):")
        for s in data["strengths"]:
            print(f"  + {s['category']}: {s['percentage']}% ({s['total']} quesiti)")
    print("=" * 72)


def main():
    parser = argparse.ArgumentParser(description="MEXT Japanese Exam Practice & Diagnostic Engine")
    parser.add_argument("--section", choices=["A", "B", "C"], help="Esegui solo una sezione specifica")
    parser.add_argument("--category", type=str, help="Filtra per categoria")
    parser.add_argument("--stats", action="store_true", help="Mostra telemetria e diagnosi del metodo")
    parser.add_argument("--timed", action="store_true", help="Abilita cronometro ufficiale 100 minuti")
    args = parser.parse_args()

    if args.stats:
        show_statistics()
        return

    db = load_database()
    filtered = db
    if args.section:
        filtered = [q for q in filtered if q.get("section") == args.section.upper()]
    if args.category:
        filtered = [q for q in filtered if args.category.lower() in q.get("category", "").lower()]

    run_drill(filtered, timed=args.timed)


if __name__ == "__main__":
    main()
