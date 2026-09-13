#!/usr/bin/env python3
"""
MEXT Embassy Oral Interview Simulator
Interactive simulation of the Japanese Studies (Nikken-sei) interview at the Embassy of Japan in Rome.
"""

import sys
import time
import random

QUESTIONS = [
    {
        "id": "INT-01",
        "category": "自己紹介 (Self-Introduction)",
        "question_ja": "まず、１分〜２分程度で自己紹介をお願いします。\n（お名前、大学での専攻、これまでの学習背景など）",
        "question_it": "Innanzitutto, faccia una breve presentazione personale di circa 1-2 minuti (nome, corso di laurea, percorso finora).",
        "key_points": [
            "Usare Kenjougo: [Nome]と申します (e non です)",
            "Menzionare l'Università di Torino (トリノ大学) e l'indirizzo (アジア・アフリカ言語文化学科)",
            "Sottolineare che si è al 2º anno e cosa si è studiato al 1º anno (grammatica, storia, cultura)"
        ],
        "model_answer_ja": "はじめまして、[氏名]と申します。現在、トリノ大学アジア・アフリカ言語文化学部の２年生でございます。１年次より日本語の文法、読解、ならびに日本史を精力的に学んでまいりました。本日はこのような貴重な面接の機会をいただき、心より感謝申し上げます。どうぞよろしくお願い申し上げます。"
    },
    {
        "id": "INT-02",
        "category": "志望動機 (Motivation)",
        "question_ja": "数ある留学プログラムの中で、なぜ日本政府（文部科学省）奨学金による日本語・日本文化研修留学生を志望されたのですか。",
        "question_it": "Tra i vari programmi di studio all'estero, perché ha scelto proprio la borsa MEXT per studenti di studi giapponesi?",
        "key_points": [
            "Non è un semplice scambio turistico o solo linguistico: è un programma di alta formazione accademica statale",
            "Opportunità di redigere un elaborato/tesina di ricerca (修了論文) sotto tutoraggio accademico giapponese",
            "Accesso a biblioteche universitarie e fonti storiche/letterarie primarie inaccessibili in Italia"
        ],
        "model_answer_ja": "一般的な語学留学や短期交換留学とは異なり、日研生プログラムは日本の国立・公立大学において専門的な指導教授のもと、学術的な調査研究を行い修了論文を執筆できる唯一無二の制度だからです。トリノ大学で培った基礎の上に、現地の一次史料や学術文献を直接紐解き、より高度な学問的知見を獲得したいと考えております。"
    },
    {
        "id": "INT-03",
        "category": "研修計画 (Study & Research Plan)",
        "question_ja": "日本での１年間の研修期間中、具体的にどのようなテーマについて研究したいとお考えですか。",
        "question_it": "Durante l'anno di studio in Giappone, su quale tema specifico intende condurre la sua ricerca?",
        "key_points": [
            "Inquadrare la ricerca nella sociologia urbana e nei 'Terzi Luoghi' (Third Places - Ray Oldenburg)",
            "Analizzare gli spazi territoriali e i circoli universitari (Sākuru/Kōryūkai) contro l'isolamento giovanile",
            "Collegare l'esperienza no-profit di 'Sinoira Gang' a Torino per la tesi di laurea triennale al rientro"
        ],
        "model_answer_ja": "私は現代日本における若者のコミュニティ形成と、対戦型アナログ・デジタルゲームを通じた社会的役割について研究したいと考えております。特に都市社会学における「サードプレイス（第三の居場所）」の観点から、大学の公認サークルや地域の交流会が青少年の孤立防止といかに結びついているかを調査し、帰国後はトリノ大学の卒業論文および地域の非営利活動に還元する所存です。"
    },
    {
        "id": "INT-04",
        "category": "配置希望大学 (University Preferences)",
        "question_ja": "配置希望申請書に記載された大学を選ばれた理由を教えてください。",
        "question_it": "Per quali motivi ha scelto le università indicate nel modulo di preferenza?",
        "key_points": [
            "Dimostrare di aver letto il Course Guide (目次 e programma dettagliato)",
            "Collegare il Tipo di corso (a: cultura/storia, b: lingua) al proprio piano di studi",
            "Non basarsi sulla notorietà della città, ma sui corsi, laboratori e docenti dell'ateneo"
        ],
        "model_answer_ja": "『コースガイド』を精読し、自身の研究関心である[分野]に関する専門講義および指導体制が最も充実している大学を選定いたしました。特に第１希望の大学におきましては、[分野]の第一人者である教授陣のゼミが開講されており、一次史料へのアクセス環境も極めて優れているためです。"
    },
    {
        "id": "INT-05",
        "category": "帰国後の進路と貢献 (Post-Program Plans)",
        "question_ja": "１年間のプログラムを終えて帰国された後、どのような計画をお持ちですか。また、日伊関係にどのように貢献したいですか。",
        "question_it": "Una volta concluso l'anno in Giappone e tornato in Italia, quali sono i suoi piani e come intende contribuire alle relazioni tra Italia e Giappone?",
        "key_points": [
            "FONDAMENTALE: Dichiarare con fermezza che si tornerà a UniTO per completare il 3º anno e laurearsi!",
            "Utilizzare il lavoro svolto in Giappone come base della Tesi di Laurea Triennale",
            "Obiettivi futuri: prosecuzione magistrale, mediazione culturale, diplomazia o divulgazione accademica"
        ],
        "model_answer_ja": "日本での１年間の研修終了後は、直ちにトリノ大学に復学し、３年次の学業を修めて日本で収集した資料をもとに卒業論文を執筆・完成させます。将来的には、この貴重な学びを活かし、学術・文化・経済の各分野において日本とイタリアの相互理解を深める架け橋として貢献したいと存じます。"
    },
    {
        "id": "INT-06",
        "category": "現地研究の必然性 (Why Japan & Not Turin?)",
        "question_ja": "なぜトリノ大学の講義や文献調査だけでは不十分で、実際に日本に滞在して研究する必要があるのですか。",
        "question_it": "Perché le lezioni e le ricerche bibliografiche a UniTO non sono sufficienti ed è indispensabile svolgere la ricerca sul campo in Giappone?",
        "key_points": [
            "La sociologia dei Terzi Luoghi richiede ricerca etnografica e osservazione partecipante in situ",
            "Accesso a fonti primarie e bollettini universitari (紀要 - Kiyō) non digitalizzati né disponibili in Europa",
            "Interviste dirette a gestori di spazi giovanili, card room e responsabili di circoli universitari"
        ],
        "model_answer_ja": "第三の居場所に関する研究は、二次文献の精読のみでは決して完結いたしません。現地のカードショップや大学公認サークルにおける参与観察、運営者や若年層への実地聞き取り調査、そして日本の大学紀要にのみ所蔵されている最新の社会学一次資料の収集が不可欠だからでございます。現地で得た確かな実証データをトリノ大学の卒業研究に還元したいと考えております。"
    }
]


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
