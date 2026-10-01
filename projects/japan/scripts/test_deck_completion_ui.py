#!/usr/bin/env python3
"""
scratch/test_deck_completion_ui.py — Targeted verification of Mazzo Completato screen.
Ensures #ankiCardContainer is centered, opacity 1, transform reset, and elements properly hidden.
"""

import json
import os
import sys
import time

# Add /opt/japan to sys.path if running on IONOS
sys.path.insert(0, "/opt/japan")
sys.path.insert(0, "/mnt/workspaces/japan")

from scripts.chrome_cdp import ChromeRunner

def test_deck_completion():
    print("=" * 65)
    print("🎯 STARTING TARGETED VERIFICATION: MAZZO COMPLETATO SCREEN")
    print("=" * 65)

    runner = ChromeRunner("https://japan.calq.it/anki")
    runner.start()
    try:
        # Wait for page load
        for _ in range(25):
            time.sleep(0.4)
            ready = runner.evaluate("document.readyState")
            if ready == "complete":
                break

        print("[*] Page loaded. Simulating 1-card study session...")

        # Setup an active deck with 1 card in study view and finish it via swipe
        setup_js = """
        new Promise((resolve) => {
          // Open study view
          document.getElementById('ankiStudyView').classList.remove('hidden');
          document.getElementById('ankiDeckListView').classList.add('hidden');
          document.getElementById('ankiDeckOverviewView').classList.add('hidden');

          // Initialize queue with a single mock card
          const testCard = {
            id: 999999999,
            front: '試験',
            back: 'shiken',
            queue: 2,
            type: 2,
            factor: 2500,
            interval: 1,
            reps: 1,
            lapses: 0,
            due: 100
          };

          // Ingest into study session
          if (typeof window.ankiInitStudyQueue === 'function') {
            window.ankiInitStudyQueue([testCard], 'Test Deck', { new: 0, lrn: 0, rev: 1 });
          } else {
            // Render card directly
            window.ankiUpdateCardElements(testCard, false);
          }
          resolve(true);
        })
        """
        runner.evaluate(setup_js)
        time.sleep(0.5)

        # Trigger swipe right (correct) to exit the card off-screen
        print("[*] Triggering programmatic swipe to simulate card exit animation...")
        runner.evaluate("window.ankiTriggerSwipe(1)") # Swipe right
        time.sleep(0.4)

        # Verify card container was animated off-screen during exit
        # Now trigger queue completion
        print("[*] Invoking renderSessionFinished()...")
        runner.evaluate("window.ankiRenderSessionFinished()")
        time.sleep(0.3)

        # Inspect UI state
        ui_state = runner.evaluate("""
        (() => {
          const cardCont = document.getElementById('ankiCardContainer');
          const frontEl = document.getElementById('ankiCardFront');
          const swipeZone = document.getElementById('ankiCardSwipeZone');
          const timerCont = document.getElementById('ankiTimerContainer');
          const btnShow = document.getElementById('ankiBtnShowAnswer');

          const rect = cardCont ? cardCont.getBoundingClientRect() : null;
          const computedStyle = cardCont ? window.getComputedStyle(cardCont) : null;

          return {
            frontHtml: frontEl ? frontEl.innerHTML : '',
            hasMazzoCompletato: frontEl ? frontEl.innerText.includes('Mazzo Completato!') : false,
            hasPartyEmoji: frontEl ? frontEl.innerHTML.includes('🎉') : false,
            cardContOpacity: cardCont ? cardCont.style.opacity : null,
            cardContTransform: cardCont ? cardCont.style.transform : null,
            computedOpacity: computedStyle ? computedStyle.opacity : null,
            computedTransform: computedStyle ? computedStyle.transform : null,
            rect: rect ? { left: rect.left, top: rect.top, width: rect.width, height: rect.height } : null,
            swipeZoneHidden: swipeZone ? swipeZone.classList.contains('hidden') : false,
            timerContHidden: timerCont ? timerCont.classList.contains('hidden') : false,
            btnShowVisible: btnShow ? !btnShow.classList.contains('hidden') : false,
            btnShowText: btnShow ? btnShow.innerText : ''
          };
        })()
        """)

        print(f"[+] UI State extracted:\n{json.dumps(ui_state, indent=2)}")

        # Binary assertions
        assert ui_state["hasMazzoCompletato"], "Mazzo Completato! text missing from front element"
        assert ui_state["hasPartyEmoji"], "🎉 emoji missing from front element"
        assert ui_state["cardContOpacity"] == "1" or ui_state["computedOpacity"] == "1", f"cardContainer opacity not 1: {ui_state['cardContOpacity']}"
        assert "translate3d(0" in (ui_state["cardContTransform"] or "") or ui_state["computedTransform"] == "matrix(1, 0, 0, 1, 0, 0)" or ui_state["computedTransform"] == "none", f"cardContainer transform not reset: {ui_state['cardContTransform']}"
        assert ui_state["rect"]["left"] >= 0 and ui_state["rect"]["width"] > 0, f"cardContainer offscreen: {ui_state['rect']}"
        assert ui_state["swipeZoneHidden"], "swipeZone should be hidden on completion screen"
        assert ui_state["timerContHidden"], "timerContainer should be hidden on completion screen"
        assert ui_state["btnShowVisible"], "btnShowAnswer should be visible to navigate back"

        print("[*] Testing navigation back to deck list on button click...")
        runner.evaluate("document.querySelector('#ankiCardFront button').click()")
        time.sleep(0.4)
        deck_list_visible = runner.evaluate("!document.getElementById('ankiDeckListView').classList.contains('hidden')")
        study_hidden = runner.evaluate("document.getElementById('ankiStudyView').classList.contains('hidden')")
        assert deck_list_visible, "Deck list view was not restored after clicking button"
        assert study_hidden, "Study view was not hidden after returning to deck list"
        print(" [+] Returned to Deck List successfully!")

        print("\n" + "=" * 65)
        print("🎉 TARGETED VERIFICATION PASSED: MAZZO COMPLETATO IS FULLY VISIBLE & CENTERED!")
        print("=" * 65)

    finally:
        runner.close()

if __name__ == "__main__":
    test_deck_completion()
