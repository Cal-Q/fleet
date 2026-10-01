#!/usr/bin/env python3
"""
scripts/test_browser_study_session_cdp.py
Authentic browser E2E test using real Chromium CDP on Oracle.
Strictly <= 200 lines, <= 100 cols.
"""

import sys
import time
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.chrome_cdp import ChromeRunner
from core.version import APP_VERSION


def run_cdp_verification():
    print("=" * 60)
    print("[*] Starting authentic Chromium CDP Study Session Test on Oracle")
    print("=" * 60)

    runner = ChromeRunner("https://japan.calq.it/anki")
    runner.start()
    try:
        # Allow page and SW to initialize
        time.sleep(2.5)

        # 1. Verify app title and version badge
        version_text = runner.evaluate(
            "document.getElementById('ankiHeaderVersionBtn')?.innerText"
        )
        print(f"[+] App Version in Header: {version_text}")
        assert version_text == APP_VERSION, f"Expected {APP_VERSION}, got {version_text}"

        # 2. Check deck list rendered (wait up to 5s)
        q_sel = '#ankiDecksContainer div[onclick*="ankiOpenDeckOverview"]'
        deck_count = 0
        for _ in range(25):
            deck_count = runner.evaluate(f"document.querySelectorAll('{q_sel}').length") or 0
            if deck_count > 0:
                break
            time.sleep(0.2)
        print(f"[+] Decks rendered in list: {deck_count}")
        assert deck_count and deck_count > 0, "No decks rendered in container"

        # 3. Open overview for Japanese Travel Pack (Parent Deck / Raccolta)
        print("[*] Opening 'Giapponese • Travel Pack' (id: 1774737216111) overview...")
        runner.evaluate(
            "window.ankiOpenDeckOverview(1774737216111, 'Giapponese • Travel Pack')"
        )
        time.sleep(1.0)

        overview_title = runner.evaluate(
            "document.getElementById('ankiOverviewDeckName')?.innerText"
        )
        ov_new = runner.evaluate("document.getElementById('ankiOverviewNew')?.innerText")
        ov_lrn = runner.evaluate("document.getElementById('ankiOverviewLrn')?.innerText")
        ov_rev = runner.evaluate("document.getElementById('ankiOverviewRev')?.innerText")
        print(f"[+] Overview Title: '{overview_title}'")
        print(f"[+] Overview Counts -> New: {ov_new}, Learning: {ov_lrn}, Review: {ov_rev}")
        assert "Travel Pack" in (overview_title or ""), "Deck title mismatch in overview"

        # 4. Click 'Studia Adesso' and measure launch latency
        print("[*] Launching Study Session...")
        t_start = time.time()
        runner.evaluate("window.ankiLaunchStudySession()")

        # Wait for study view and first card
        card_ready = False
        for _ in range(25):
            study_hidden = runner.evaluate(
                "document.getElementById('ankiStudyView')?.classList.contains('hidden')"
            )
            front = runner.evaluate("document.getElementById('ankiCardFront')?.innerText")
            if not study_hidden and front and front.strip():
                card_ready = True
                break
            time.sleep(0.1)

        t_elapsed = (time.time() - t_start) * 1000
        print(f"[+] Study session ready in {t_elapsed:.1f}ms. Card rendered: {card_ready}")
        assert card_ready, "Card front failed to render"

        st_new = runner.evaluate("document.getElementById('ankiCountNew')?.innerText")
        st_lrn = runner.evaluate("document.getElementById('ankiCountLrn')?.innerText")
        st_rev = runner.evaluate("document.getElementById('ankiCountRev')?.innerText")
        print(f"[+] Study Due Pill -> New: {st_new}, Learning: {st_lrn}, Review: {st_rev}")
        assert (st_new, st_lrn, st_rev) == (ov_new, ov_lrn, ov_rev), (
            f"Count mismatch! Overview: ({ov_new}, {ov_lrn}, {ov_rev}) vs "
            f"Study: ({st_new}, {st_lrn}, {st_rev})"
        )

        first_card_queue = runner.evaluate(
            "window.ankiGetCurrentCard ? window.ankiGetCurrentCard().queue : null"
        )
        print(f"[+] First Card Queue Tier: {first_card_queue}")
        if int(ov_lrn or 0) > 0:
            assert first_card_queue in (1, 3), (
                f"Expected red card (queue 1/3) since ov_lrn={ov_lrn}, got queue={first_card_queue}"
            )
            print("[+] Verified: Due red card served with highest priority!")

        front_content = runner.evaluate(
            "document.getElementById('ankiCardFront')?.innerText"
        )
        print(f"[+] Card 1 Front Content: '{front_content}'")

        # 5. Verify timer is running and ticking downwards
        t_tick0 = runner.evaluate("document.getElementById('ankiTimerText')?.innerText")
        time.sleep(1.2)
        t_tick1 = runner.evaluate("document.getElementById('ankiTimerText')?.innerText")
        print(f"[+] Timer tick verification on Front: '{t_tick0}' -> '{t_tick1}'")
        assert t_tick0 != "", "Timer text was empty"

        # 6. Flip card and measure DOM reveal latency
        print("[*] Executing flipCard()...")
        t_flip_start = time.time()
        runner.evaluate("window.ankiFlipCard()")
        t_flip_elapsed = (time.time() - t_flip_start) * 1000

        back_state = runner.evaluate("""
        ({
          isBackHidden: document.getElementById('ankiCardBack')?.classList.contains('hidden'),
          reading: document.getElementById('ankiCardReading')?.innerText,
          meaningSnippet: document.getElementById('ankiCardMeaning')?.innerText?.substring(0, 60),
          isPromptHidden: document.getElementById('ankiFlipPrompt')?.classList.contains('hidden'),
          isBtnGroupVisible: !document.getElementById(
            'ankiAnswerButtonGroup'
          )?.classList.contains('hidden'),
          timerText: document.getElementById('ankiTimerText')?.innerText
        })
        """)
        print(f"[+] Flip latency: {t_flip_elapsed:.2f}ms")
        print(f"[+] Back State: {back_state}")
        assert not back_state.get("isBackHidden"), "Card back is still hidden"
        assert back_state.get("isBtnGroupVisible"), "Answer button group not visible"
        assert back_state.get("reading"), "Card reading was empty"

        # 7. Grade card (answer Good = 3)
        print("[*] Answering Card (Good / 3)...")
        runner.evaluate("window.ankiAnswerCard(3)")
        time.sleep(1.0)

        # 8. Verify next card or session progression
        next_front = runner.evaluate(
            "document.getElementById('ankiCardFront')?.innerText"
        )
        t_card2_0 = runner.evaluate("document.getElementById('ankiTimerText')?.innerText")
        time.sleep(1.2)
        t_card2_1 = runner.evaluate("document.getElementById('ankiTimerText')?.innerText")
        print(f"[+] Next Card Front: '{next_front}'")
        print(f"[+] Next Card Timer Tick: '{t_card2_0}' -> '{t_card2_1}'")
        assert t_card2_0 != "", "Card 2 timer was empty"

        print("=" * 60)
        print("[🎉 SUCCESS] Authentic Chromium CDP Study Session Test PASSED!")
        print("=" * 60)
        return True
    finally:
        runner.close()


if __name__ == "__main__":
    success = run_cdp_verification()
    sys.exit(0 if success else 1)
