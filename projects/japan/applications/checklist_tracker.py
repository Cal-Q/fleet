#!/usr/bin/env python3
"""
MEXT Japanese Studies Scholarship - Application Dossier Auditor & Tracker
Tailored for UniTO (Università degli Studi di Torino) applicants.
"""

import os
import sys
import json
import argparse
from datetime import datetime

STATUS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "application_status.json")

DEFAULT_ITEMS = [
    {
        "id": "app_form",
        "name": "Application Form (Modulo di Candidatura FY2027)",
        "file_path": "applications/2026_Application_Form.pdf",
        "status": "pending",
        "notes": "Compilare in lingua inglese o giapponese (digitato). Focus su 研修目的 (motivazioni e piano di studi 2027/2028).",
        "mandatory": True
    },
    {
        "id": "placement_form",
        "name": "Placement Preference Application Form (Scelta Università)",
        "file_path": "applications/2026_Placement_Preference_Form.pdf",
        "status": "pending",
        "notes": "Indicare fino a 3 università selezionate dal Course Guide (Tipo a: Cultura/Storia, Tipo b: Lingua).",
        "mandatory": True
    },
    {
        "id": "unito_transcript",
        "name": "Certificato di iscrizione con esami (UniTO - Segreteria Polo Umanistico)",
        "file_path": "applications/unito_iscrizione_esami_timbrato.pdf",
        "status": "pending",
        "notes": "ATTENZIONE: Timbro a inchiostro e firma originale della segreteria (Complesso Aldo Moro / Palazzo Nuovo). Autocertificazione NON valida.",
        "mandatory": True
    },
    {
        "id": "recommendation_letter",
        "name": "Recommendation Letter (Lettera di Raccomandazione)",
        "file_path": "applications/unito_recommendation_letter.pdf",
        "status": "pending",
        "notes": "Docente di giapponese/storia di UniTO su carta intestata d'ateneo. Modello MEXT solo indicativo.",
        "mandatory": True
    },
    {
        "id": "certificate_of_health",
        "name": "Certificate of Health (Certificato Medico Ufficiale MEXT)",
        "file_path": "applications/2026_Certificate_of_Health.pdf",
        "status": "pending",
        "notes": "Compilato, timbrato e firmato da medico abilitato con esami sangue/urine/Rx torace e punto 7 compilato. Consegnabile anche a mano al test.",
        "mandatory": True
    },
    {
        "id": "jlpt_cert",
        "name": "Copia Certificato JLPT (Score Report)",
        "file_path": "applications/jlpt_score_report.pdf",
        "status": "optional",
        "notes": "Conseguito negli ultimi 2 anni. Deve mostrare nome, livello e punteggio dettagliato.",
        "mandatory": False
    }
]

EMBASSY_RULES = {
    "embassy_email": "ryugaku@ro.mofa.go.jp",
    "embassy_phone": "06-487991",
    "email_subject": "Candidatura Japanese Studies 2027",
    "max_email_attachment_bytes": 10 * 1024 * 1024,  # 10 MB limit
    "deadline_note": "Entro inizio febbraio 2027 ore 8:00 a.m. (telefonare in Ambasciata dopo l'invio per conferma ricezione)."
}


def load_state():
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Avviso: errore nella lettura di {STATUS_FILE} ({e}). Ripristino default.")
    return {"items": DEFAULT_ITEMS, "metadata": EMBASSY_RULES, "last_updated": datetime.now().isoformat()}


def save_state(state):
    state["last_updated"] = datetime.now().isoformat()
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def display_status(state):
    print("=" * 76)
    print("🇯🇵 AMBASCIATA DEL GIAPPONE IN ITALIA — MEXT JAPANESE STUDIES DOSSIER")
    print("🎓 Candidato: Università degli Studi di Torino (UniTO) — Lingue e Culture Asia e Africa")
    print("=" * 76)
    
    total_size = 0
    all_mandatory_ready = True
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    print(f"{'STATO':<12} | {'DOCUMENTO':<38} | {'FILE LOCALE':<18}")
    print("-" * 76)

    for item in state.get("items", []):
        status_icon = {
            "completed": "✅ PRONTO",
            "pending": "⏳ IN ATTESA",
            "missing": "❌ MANCANTE",
            "optional": "⚪ FACOLTATIVO"
        }.get(item["status"], "❓")

        # Check local file existence and size
        full_path = os.path.join(base_dir, item["file_path"])
        file_info = "Non trovato"
        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            total_size += size
            file_info = f"{size / 1024:.1f} KB"
        else:
            if item["mandatory"] and item["status"] != "completed":
                all_mandatory_ready = False

        print(f"{status_icon:<12} | {item['name'][:36]:<38} | {file_info:<18}")
        print(f"   ↳ {item['notes']}")

    print("-" * 76)
    mb_size = total_size / (1024 * 1024)
    max_mb = EMBASSY_RULES["max_email_attachment_bytes"] / (1024 * 1024)
    print(f"📦 Dimensione totale allegati stimata: {mb_size:.2f} MB / Limite Ambasciata: {max_mb:.1f} MB")
    if total_size > EMBASSY_RULES["max_email_attachment_bytes"]:
        print("🚨 ATTENZIONE: Gli allegati superano i 10MB! Inviare la documentazione suddivisa in più email.")
    else:
        print("✅ Dimensione conforme ai limiti del server email dell'Ambasciata.")

    print("\n📬 RECAPITO AMBASCIATA:")
    print(f"  • Email: {EMBASSY_RULES['embassy_email']}")
    print(f"  • Oggetto: \"{EMBASSY_RULES['email_subject']}\"")
    print(f"  • Telefono verifica: {EMBASSY_RULES['embassy_phone']}")
    print(f"  • Regola: {EMBASSY_RULES['deadline_note']}")
    print("=" * 76)


def set_status(item_id, status):
    valid_statuses = ["completed", "pending", "missing", "optional"]
    if status not in valid_statuses:
        print(f"Errore: stato non valido. Scegliere tra: {', '.join(valid_statuses)}")
        sys.exit(1)
    state = load_state()
    found = False
    for item in state.get("items", []):
        if item["id"] == item_id:
            item["status"] = status
            found = True
            print(f"Aggiornato '{item['name']}' -> {status}")
            break
    if not found:
        print(f"Errore: nessun documento con ID '{item_id}'.")
        print("ID disponibili: " + ", ".join([i["id"] for i in state.get("items", [])]))
        sys.exit(1)
    save_state(state)


def main():
    parser = argparse.ArgumentParser(description="MEXT Application Dossier Tracker")
    parser.add_argument("--status", action="store_true", help="Mostra lo stato del dossier")
    parser.add_argument("--set", nargs=2, metavar=("DOC_ID", "STATUS"), help="Aggiorna lo stato (es. --set unito_transcript completed)")
    args = parser.parse_args()

    state = load_state()

    if args.set:
        set_status(args.set[0], args.set[1])
    else:
        display_status(state)


if __name__ == "__main__":
    main()
