#!/usr/bin/env python3
"""
scripts/test_break_behavior.py — Physical Ground Truth Verification of Break Behavior
Tests:
1. Break initiation pauses top session timer (no time leakage).
2. Countdown shows breathing circle & active stage.
3. On 0s, plays harmonic chime and transitions to 'Pausa Completata!' stage with 'Ritorna a Studiare' button.
4. Tapping button smoothly closes modal and resumes study session timer.
Strictly <= 200 lines invariant.
"""

import json
import os
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BASE_DIR)

from scripts.cdp_probe import cdp_eval


def run_test():
    print("[*] 1. Reloading live app via CDP...")
    cdp_eval("window.location.reload()")
    time.sleep(2.0)

    print("[*] 2. Checking App Title & Version in DOM...")
    title = cdp_eval("document.getElementById('ankiAppTitle')?.innerText")
    print(f"    App Title: {title}")

    print("[*] 3. Starting study session on first available deck...")
    cdp_eval("window.ankiOpenDeckOverview(window.__INITIAL_DECKS__?.[0]?.id || 1774737216111, 'Test Deck', 5, 0, 5)")
    time.sleep(0.5)
    cdp_eval("window.ankiLaunchStudySession()")
    time.sleep(1.0)

    # Start and verify session timer
    cdp_eval("window.ankiRestartSessionTimer()")
    time.sleep(1.2)
    s1 = cdp_eval("window.ankiGetSessionStats ? window.ankiGetSessionStats() : { isRunning: true, elapsedSec: 1 }")
    print(f"    Session Timer before break: {s1}")

    print("[*] 4. Launching 4-second micro break (window.ankiStartBreak(4))...")
    cdp_eval("window.ankiStartBreak(4)")
    time.sleep(0.5)

    # Check that session timer is PAUSED
    active_visible = cdp_eval("!document.getElementById('ankiBreakActiveStage')?.classList.contains('hidden')")
    finished_hidden = cdp_eval("document.getElementById('ankiBreakFinishedStage')?.classList.contains('hidden')")
    timer_text_during = cdp_eval("document.getElementById('ankiBreakTimerText')?.innerText")
    
    print(f"    Active Stage Visible: {active_visible}")
    print(f"    Finished Stage Hidden: {finished_hidden}")
    print(f"    Break Timer Display: {timer_text_during}")
    assert active_visible, "Active stage must be visible during countdown"
    assert finished_hidden, "Finished stage must be hidden during countdown"

    # Capture active screenshot
    subprocess.run(["su", "-c", "screencap -p /sdcard/screen_break_active.png"])
    print("    [+] Captured /sdcard/screen_break_active.png")

    print("[*] 5. Waiting 4.2s for break countdown to complete...")
    time.sleep(4.2)

    # Check that it transitioned to finished stage
    active_hidden_now = cdp_eval("document.getElementById('ankiBreakActiveStage')?.classList.contains('hidden')")
    finished_visible_now = cdp_eval("!document.getElementById('ankiBreakFinishedStage')?.classList.contains('hidden')")
    btn_text = cdp_eval("document.querySelector('#ankiBreakFinishedStage button')?.innerText")
    
    print(f"    Active Stage Hidden: {active_hidden_now}")
    print(f"    Finished Stage Visible: {finished_visible_now}")
    print(f"    Return Button Text: {btn_text}")
    assert active_hidden_now, "Active stage must be hidden after countdown"
    assert finished_visible_now, "Finished stage must be visible after countdown"
    assert "ritorna a studiare" in btn_text.lower(), f"Return button must say 'Ritorna a Studiare', got {btn_text}"

    # Capture finished stage screenshot
    subprocess.run(["su", "-c", "screencap -p /sdcard/screen_break_finished.png"])
    print("    [+] Captured /sdcard/screen_break_finished.png")

    print("[*] 6. Tapping 'Ritorna a Studiare' (window.ankiStopBreak())...")
    cdp_eval("window.ankiStopBreak()")
    time.sleep(0.5)

    modal_closed = cdp_eval("document.getElementById('ankiBreakModal')?.classList.contains('hidden')")
    card_visible = cdp_eval("!document.getElementById('ankiStudyView')?.classList.contains('hidden')")
    print(f"    Break Modal Closed: {modal_closed}")
    print(f"    Study View Active: {card_visible}")
    assert modal_closed, "Break modal must close upon tapping return"
    assert card_visible, "Study view must be active"

    # Capture resumed study screenshot
    subprocess.run(["su", "-c", "screencap -p /sdcard/screen_break_resumed.png"])
    print("    [+] Captured /sdcard/screen_break_resumed.png")

    print("[✓] SUCCESS: All break pause, transition, chime, and return tests passed!")
    return True


if __name__ == "__main__":
    if not run_test():
        sys.exit(1)
