#!/usr/bin/env python3
"""
scripts/test_offline_e2e.py — Headless Chromium Offline Emulation E2E Test Suite
Tests PWA offline caching, queue advance without premature completion,
IndexedDB outbox persistence, reconnection atomic batch sync, and SQLite integrity.
Strictly <= 200 lines invariant.
"""

import os
import sqlite3
import sys
import time
from scripts.chrome_cdp import ChromeRunner

DB_PATH = "/opt/japan/.local/share/Anki2/User 1/collection.anki2"
TARGET_DECK_ID = 1758314901201
TARGET_DECK_NAME = "[JAP]::Kanji -> Writing Practice"


def get_revlog_state():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), COALESCE(MAX(id), 0) FROM revlog")
    count, max_id = cur.fetchone()
    conn.close()
    return count, max_id


def count_idb_outbox(runner: ChromeRunner) -> int:
    js = """
    new Promise((resolve) => {
      const req = indexedDB.open('anki_offline_db', 1);
      req.onsuccess = () => {
        try {
          const db = req.result;
          const tx = db.transaction('outbox', 'readonly');
          const countReq = tx.objectStore('outbox').count();
          countReq.onsuccess = () => resolve(countReq.result);
          countReq.onerror = () => resolve(-1);
        } catch (e) { resolve(-1); }
      };
      req.onerror = () => resolve(-1);
    })
    """
    return runner.evaluate(js) or 0


def run_offline_e2e():
    print("\n" + "=" * 65)
    print("🚀 STARTING E2E HEADLESS CHROMIUM OFFLINE EMULATION AUDIT")
    print("=" * 65)

    initial_rev_count, initial_max_id = get_revlog_state()
    print(f"[*] Initial SQLite state: {initial_rev_count} reviews, max id: {initial_max_id}")

    runner = ChromeRunner("https://japan.calq.it/anki")
    runner.start()
    try:
        print("[*] Chromium started. Waiting for page load and Service Worker caching...")
        for _ in range(25):
            time.sleep(0.5)
            ready = runner.evaluate("document.readyState")
            deck_count = runner.evaluate("document.querySelectorAll('#ankiDecksContainer > div').length") or 0
            loading = runner.evaluate("Boolean(document.getElementById('ankiDecksContainer')?.innerText?.includes('Caricamento'))")
            if ready == "complete" and deck_count > 1 and not loading:
                break

        print(f" [+] Online Stage: Loaded {deck_count} decks. Allowing prefetch...")
        assert deck_count and deck_count > 1, f"Expected >1 decks, found {deck_count}"
        print(f"[*] Waiting for target deck {TARGET_DECK_ID} to cache in IndexedDB...")
        check_js = f"""
        new Promise((res) => {{
          const req = indexedDB.open('anki_offline_db', 1);
          req.onsuccess = () => {{
            try {{
              const tx = req.result.transaction('deck_cards', 'readonly');
              const g = tx.objectStore('deck_cards').get({TARGET_DECK_ID});
              g.onsuccess = () => res(g.result?.cards?.length || 0);
              g.onerror = () => res(0);
            }} catch (e) {{ res(0); }}
          }};
          req.onerror = () => res(0);
        }})
        """
        cached_count = 0
        for _ in range(30):
            cached_count = runner.evaluate(check_js) or 0
            if cached_count > 0:
                break
            time.sleep(0.5)
        print(f" [+] Target deck cached with {cached_count} cards in IndexedDB.")
        assert cached_count > 0, f"Deck {TARGET_DECK_ID} failed to cache in IndexedDB"

        print("\n[*] EMULATING OFFLINE DISCONNECTION (Network.emulateNetworkConditions)...")
        runner.emulate_offline(True)
        time.sleep(0.5)

        online = runner.evaluate("navigator.onLine")
        print(f" [+] Network status: navigator.onLine = {online}")
        assert online is False, "Browser is not reporting offline"

        print(f"[*] Launching deck session offline (Deck: {TARGET_DECK_NAME})...")
        runner.evaluate(f"window.ankiOpenDeckOverview({TARGET_DECK_ID}, '{TARGET_DECK_NAME}', 10, 0, 10)")
        time.sleep(0.3)
        runner.evaluate("window.ankiLaunchStudySession()")

        card_visible = False
        for _ in range(15):
            time.sleep(0.3)
            if runner.evaluate("Boolean(window.ankiGetCurrentCard())"):
                card_visible = True
                break
        assert card_visible, "Current card failed to render offline"

        cards_reviewed = 0
        target_reviews = 5
        print(f"[*] Performing {target_reviews} offline reviews (Again + Good)...")

        for i in range(target_reviews):
            curr_card = runner.evaluate("window.ankiGetCurrentCard()")
            cid = curr_card.get("id") if curr_card else None
            assert cid, f"No valid card at step {i}"

            runner.evaluate("window.ankiFlipCard()")
            time.sleep(0.15)

            # Alternate grades: first card Again (1), remaining Good (3)
            grade = 1 if i == 0 else 3
            runner.evaluate(f"window.ankiAnswerCard({grade})")
            cards_reviewed += 1
            time.sleep(0.25)

            # Regression check Bug 1: Must NOT falsely finish session
            front_text = str(runner.evaluate("document.getElementById('ankiCardFront')?.innerText") or "")
            is_premature_finished = "Mazzo Completato" in front_text
            assert not is_premature_finished, f"REGRESSION: Session falsely finished after {cards_reviewed} cards!"
            print(f"  [+] Reviewed card {i+1}/{target_reviews} (cid={cid}, grade={grade}) - Queue active")

        # Verify Outbox accumulation
        outbox_count = count_idb_outbox(runner)
        print(f" [+] IndexedDB Outbox holds {outbox_count} reviews offline (expected {target_reviews})")
        assert outbox_count == target_reviews, f"Expected {target_reviews} outbox items, got {outbox_count}"

        # Regression check Bug 2: Reconnection & Atomic Batch Flush
        print("\n[*] RESTORING NETWORK CONNECTIVITY (Network.emulateNetworkConditions: online)...")
        runner.emulate_offline(False)
        time.sleep(0.5)
        assert runner.evaluate("navigator.onLine") is True, "Failed to restore online state"

        print("[*] Navigating to deck list to trigger atomic flush...")
        runner.evaluate("window.ankiShowDeckList()")
        time.sleep(2.5)

        remaining_outbox = count_idb_outbox(runner)
        print(f" [+] Post-sync IndexedDB Outbox count: {remaining_outbox}")
        assert remaining_outbox == 0, f"Expected empty outbox post-sync, found {remaining_outbox}"

        # Verify Ground Truth in SQLite DB
        final_rev_count, final_max_id = get_revlog_state()
        new_reviews = final_rev_count - initial_rev_count
        print(f" [+] Final SQLite state: {final_rev_count} reviews (+{new_reviews}), max id: {final_max_id}")
        assert new_reviews == target_reviews, f"Expected +{target_reviews} revlog rows in DB, got +{new_reviews}"

        # Verify unique IDs and non-collision in revlog
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(f"SELECT id, cid, ease, time FROM revlog WHERE id > {initial_max_id} ORDER BY id ASC")
        rows = cur.fetchall()
        conn.close()

        print(f" [+] Verifying persisted revlog entries ({len(rows)} entries):")
        unique_ids = set()
        for r in rows:
            unique_ids.add(r[0])
            print(f"     -> id={r[0]}, cid={r[1]}, ease={r[2]}, time={r[3]}ms")
        assert len(unique_ids) == target_reviews, "Primary key collision detected in batch revlog insertion!"

        print("\n" + "=" * 65)
        print("🎉 ALL OFFLINE E2E TESTS PASSED WITH 100% EMPIRICAL PROOF!")
        print("=" * 65)
        return True

    finally:
        runner.close()


if __name__ == "__main__":
    success = run_offline_e2e()
    sys.exit(0 if success else 1)
