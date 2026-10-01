#!/usr/bin/env python3
"""
scripts/test_exam_features_e2e.py — Headless E2E Verification of Exam Upgrades.
Verifies Resilient Timer, Parti Mancanti, Non lo so, Confidence 1-9 & Hotkeys.
Strictly <= 200 lines invariant.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chrome_cdp import ChromeRunner


def test_exam_upgrades():
    print("[*] Launching Headless CDP Exam Features Audit...")
    runner = ChromeRunner(target_url="https://japan.calq.it/", port=9224)
    runner.start()
    try:
        for _ in range(25):
            time.sleep(0.3)
            if runner.evaluate("document.readyState") == "complete":
                break

        # 1. Switch to Exam Tab and Load Section A
        runner.evaluate("window.switchTab('exams'); window.loadExam('A');")
        time.sleep(0.8)

        # 2. Resilient Timer and Reset Button
        timer_text = runner.evaluate("document.getElementById('timeElapsed')?.innerText")
        reset_btn = runner.evaluate("Boolean(document.getElementById('btnResetTimer'))")
        print(f" [+] Check 1: Timer Display='{timer_text}', ResetBtn={reset_btn}")
        assert timer_text and reset_btn, "Timer display or Reset button missing"

        # 3. Parti Mancanti Toggle & Character Selection
        missing_btn = runner.evaluate(
            "Boolean(document.getElementById('btnToggleMissingParts'))"
        )
        print(f" [+] Check 2.1: Missing Parts Toggle Btn={missing_btn}")
        assert missing_btn, "Missing parts button missing"

        runner.evaluate("window.toggleMissingPartsMode()")
        is_mode_on = runner.evaluate("window.isMissingPartsActive()")
        char_count = runner.evaluate(
            "document.querySelectorAll('#examSingleContainer span.clickable-char').length"
        )
        print(f" [+] Check 2.2: Mode ON={is_mode_on}, Clickable Chars={char_count}")
        assert is_mode_on and char_count > 0, "Missing parts mode failed to activate chars"

        runner.evaluate(
            "document.querySelector('#examSingleContainer span.clickable-char')?.click()"
        )
        unknowns = runner.evaluate(
            "window.getUnknownCharacters(window.getCurrentQuestion()?.id)"
        )
        print(f" [+] Check 2.3: Selected Unknown Characters={unknowns}")
        assert unknowns and len(unknowns) > 0, "Character selection failed"

        runner.evaluate("window.toggleMissingPartsMode()")
        is_mode_off = not runner.evaluate("window.isMissingPartsActive()")
        print(f" [+] Check 2.4: Mode OFF={is_mode_off}")
        assert is_mode_off, "Missing parts toggle off failed"

        # 4. Don't Know ("Non lo so") Button
        dontknow_btn = runner.evaluate(
            "Boolean(document.querySelector('.exam-dontknow-btn'))"
        )
        print(f" [+] Check 3.1: Don't Know Button Present={dontknow_btn}")
        assert dontknow_btn, "Don't know button missing"

        runner.evaluate("document.querySelector('.exam-dontknow-btn')?.click()")
        user_ans = runner.evaluate(
            "window.getUserAnswer(window.getCurrentQuestion()?.id)"
        )
        print(f" [+] Check 3.2: User Answer Recorded={user_ans}")
        assert user_ans == "DONT_KNOW", f"Expected DONT_KNOW, got {user_ans}"

        # 5. Confidence Bar (1-9)
        sel_conf = '#examSingleContainer button[onclick*="setConfidence"]'
        conf_btns = runner.evaluate(f"document.querySelectorAll('{sel_conf}').length")
        print(f" [+] Check 4.1: Confidence Buttons Count={conf_btns}")
        assert conf_btns == 9, f"Expected 9 confidence buttons, got {conf_btns}"

        runner.evaluate("window.setConfidenceLevel(7)")
        conf_val = runner.evaluate(
            "window.getConfidence(window.getCurrentQuestion()?.id)"
        )
        print(f" [+] Check 4.2: Selected Confidence={conf_val}")
        assert conf_val == 7, f"Expected confidence 7, got {conf_val}"

        # 6. Keybindings Hotkeys Verification
        # Key '8' sets confidence
        runner.evaluate(
            "window.dispatchEvent(new KeyboardEvent('keydown', { key: '8', bubbles: true }))"
        )
        hotkey_conf = runner.evaluate(
            "window.getConfidence(window.getCurrentQuestion()?.id)"
        )
        print(f" [+] Check 5.1: Hotkey '8' Set Confidence={hotkey_conf}")
        assert hotkey_conf == 8, f"Expected confidence 8, got {hotkey_conf}"

        # Key 'W' selects Option B
        runner.evaluate(
            "window.dispatchEvent(new KeyboardEvent('keydown', { key: 'w', bubbles: true }))"
        )
        hotkey_ans = runner.evaluate(
            "window.getUserAnswer(window.getCurrentQuestion()?.id)"
        )
        print(f" [+] Check 5.2: Hotkey 'W' Selected Option={hotkey_ans}")
        assert hotkey_ans == "B", f"Expected option B, got {hotkey_ans}"

        # Key 'X' selects Don't Know
        runner.evaluate(
            "window.dispatchEvent(new KeyboardEvent('keydown', { key: 'x', bubbles: true }))"
        )
        hotkey_x = runner.evaluate(
            "window.getUserAnswer(window.getCurrentQuestion()?.id)"
        )
        print(f" [+] Check 5.3: Hotkey 'X' Selected Don't Know={hotkey_x}")
        assert hotkey_x == "DONT_KNOW", f"Expected DONT_KNOW, got {hotkey_x}"

        # 7. Next Batch Rotation ("Nuove Domande")
        next_batch_btn = runner.evaluate(
            "Boolean(document.getElementById('btnNextBatch'))"
        )
        print(f" [+] Check 6.1: Next Batch Button Present={next_batch_btn}")
        assert next_batch_btn, "Next batch button missing"

        q_before = runner.evaluate("window.getCurrentQuestion()?.id")
        runner.evaluate("window.loadNextBatch()")
        time.sleep(0.8)
        q_after = runner.evaluate("window.getCurrentQuestion()?.id")
        print(f" [+] Check 6.2: Before={q_before}, After next batch={q_after}")
        assert q_before != q_after, f"Expected distinct question, got {q_after}"

        print("\n[🎯] ALL TARGETED EXAM UPGRADES DETERMINISTICALLY VERIFIED ON CHROMIUM CDP!")
        return True
    finally:
        runner.close()


if __name__ == "__main__":
    ok = test_exam_upgrades()
    sys.exit(0 if ok else 1)
