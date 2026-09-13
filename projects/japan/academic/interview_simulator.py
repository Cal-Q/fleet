#!/usr/bin/env python3
"""
MEXT Embassy Oral Interview Simulator
Interactive simulation of the Japanese Studies (Nikken-sei) interview at the Embassy of Japan in Rome.
"""

import sys
import time
import json
import os
import random
import sys
import time
from typing import Any, Dict, List

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "interview_questions.json")


def load_interview_questions() -> List[Dict[str, Any]]:
    """Loads interview question bank from JSON file."""
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


QUESTIONS = load_interview_questions()


def run_interview(random_mode=False):
    print("=" * 76)
    print("🎙️ AMBASCIATA DEL GIAPPONE A ROMA — SIMULATORE COLLOQUIO NIKKEN-SEI")
    print("=" * 76)
    print("Consigli prima di iniziare:")
    print("  1. Rispondi ad alta voce in giapponese come se fossi davanti alla commissione.")
    print("  2. Mantieni una postura eretta e un tono cordiale, fermo e rispettoso.")
    print("  3. Premi [INVIO] per visualizzare i punti chiave e la risposta modello.")
    print("=" * 76)

    order = list(QUESTIONS)
    if random_mode:
        random.shuffle(order)

    for i, q in enumerate(order, 1):
        print(f"\n【DOMANDA {i}/{len(order)}】 • {q['category']}")
        print("=" * 76)
        print(f"🗣️ 日本語: {q['question_ja']}")
        print(f"🇮🇹 Italiano: {q['question_it']}")
        print("-" * 76)
        
        start_t = time.time()
        input("\n👉 Premi [INVIO] quando hai completato la tua risposta orale per analizzare il feedback...")
        elapsed = int(time.time() - start_t)

        print(f"\n⏱️ Tempo di risposta impiegato: {elapsed} secondi")
        print("\n📌 Punti Chiave da Includere Assolutamente:")
        for pt in q["key_points"]:
            print(f"  • {pt}")

        print("\n✨ Esempio di Risposta Modello (敬語):")
        print(f"  「{q['model_answer_ja']}」")
        print("-" * 76)

        try:
            cont = input("\nPremi [INVIO] per passare alla prossima domanda (o 'Q' per uscire): ").strip().upper()
            if cont == "Q":
                break
        except (KeyboardInterrupt, EOFError):
            break

    print("\n" + "=" * 76)
    print("🎉 Sessione di simulazione colloquio conclusa! Ottimo lavoro.")
    print("Consiglio: Esercitati a ripetere le risposte fino a quando non suonano spontanee e fluide.")
    print("=" * 76)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="MEXT Nikken-sei Interview Simulator")
    parser.add_argument("--random", action="store_true", help="Poni le domande in ordine casuale")
    args = parser.parse_args()
    run_interview(random_mode=args.random)


if __name__ == "__main__":
    main()
