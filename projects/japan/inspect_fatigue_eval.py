#!/usr/bin/env python3
"""
inspect_fatigue_eval.py — Fatigue Model Performance & Verification Inspector

Run this tomorrow or after study sessions to verify whether the TPU model's
pause recommendations actually restored your cognitive speed and accuracy.
"""

import os
import json
import glob
from datetime import datetime

WORKSPACE_DIR = "/mnt/workspaces/japan"
LOG_FILE = os.path.join(WORKSPACE_DIR, "logs", "anki_client_events.jsonl")

def load_events():
    events = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except Exception:
                        pass
    return events

def analyze_fatigue_telemetry():
    events = load_events()
    eval_starts = [e for e in events if e.get("act") == "FATIGUE_EVAL_START"]
    eval_completes = [e for e in events if e.get("act") == "FATIGUE_EVAL_COMPLETE"]
    review_events = [e for e in events if e.get("act") == "CARD_ANSWERED"]

    print("==================================================================")
    print("      🧠 TPU COGNITIVE FATIGUE & RECOVERY VERIFICATION REPORT      ")
    print("==================================================================")
    print(f"[*] Total Logged Client Events: {len(events):,}")
    print(f"[*] Total Review Events Logged: {len(review_events):,}")
    print(f"[*] Fatigue Prompts Triggered:  {len(eval_starts)}")
    print(f"[*] Completed 10-Card Windows:  {len(eval_completes)}")
    print("------------------------------------------------------------------")

    if not eval_completes:
        print("\n[i] No completed fatigue evaluations recorded yet.")
        print("    As you study today and tomorrow, this report will automatically track:")
        print("    1. Performance recovery when you accept the recommended break.")
        print("    2. Performance decline when you dismiss the prompt and study through fatigue.")
        print("==================================================================\n")
        return

    breaks_taken = [e for e in eval_completes if e.get("det", {}).get("action") == "BREAK_TAKEN"]
    breaks_dismissed = [e for e in eval_completes if e.get("det", {}).get("action") == "DISMISSED"]

    print(f"[*] Breaks Accepted: {len(breaks_taken)}")
    print(f"[*] Breaks Dismissed (Studied Through): {len(breaks_dismissed)}")
    print("------------------------------------------------------------------")

    if breaks_taken:
        acc_deltas = [float(e["det"]["accDelta"].replace("%", "").replace("+", "")) for e in breaks_taken if "accDelta" in e.get("det", {})]
        lat_deltas = [float(e["det"]["latDeltaMs"]) for e in breaks_taken if "latDeltaMs" in e.get("det", {})]
        
        avg_acc = sum(acc_deltas) / len(acc_deltas) if acc_deltas else 0.0
        avg_lat = sum(lat_deltas) / len(lat_deltas) if lat_deltas else 0.0
        
        print("\n✅ WHEN YOU TOOK THE RECOMMENDED BREAK:")
        print(f"   • Average Accuracy Boost:  {avg_acc:+.1f}% on subsequent 10 cards")
        print(f"   • Latency Improvement:     {avg_lat:+.0f} ms ({'faster' if avg_lat < 0 else 'slower'})")
        verified_count = sum(1 for e in breaks_taken if e.get("det", {}).get("verified"))
        print(f"   • Verified Recovery Rate:  {verified_count}/{len(breaks_taken)} sessions ({verified_count/len(breaks_taken)*100:.0f}%)")

    if breaks_dismissed:
        acc_deltas_d = [float(e["det"]["accDelta"].replace("%", "").replace("+", "")) for e in breaks_dismissed if "accDelta" in e.get("det", {})]
        lat_deltas_d = [float(e["det"]["latDeltaMs"]) for e in breaks_dismissed if "latDeltaMs" in e.get("det", {})]
        
        avg_acc_d = sum(acc_deltas_d) / len(acc_deltas_d) if acc_deltas_d else 0.0
        avg_lat_d = sum(lat_deltas_d) / len(lat_deltas_d) if lat_deltas_d else 0.0

        print("\n⚠️ WHEN YOU DISMISSED & CONTINUED STUDYING:")
        print(f"   • Accuracy Impact:         {avg_acc_d:+.1f}% on subsequent 10 cards")
        print(f"   • Latency Drift:           {avg_lat_d:+.0f} ms")

    print("\n==================================================================\n")

if __name__ == "__main__":
    analyze_fatigue_telemetry()
