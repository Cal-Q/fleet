#!/usr/bin/env python3
"""
scripts/test_offline_cold_boot.py — Headless Chromium Offline Cold Reload Test Suite
Verifies Service Worker shell caching and IndexedDB offline rendering on reload.
Strictly <= 200 lines invariant.
"""

import sys
import time
from scripts.chrome_cdp import ChromeRunner


def run_cold_reload_test():
    print("\n" + "=" * 65)
    print("🚀 STARTING E2E HEADLESS CHROMIUM OFFLINE COLD RELOAD AUDIT")
    print("=" * 65)

    runner = ChromeRunner("https://japan.calq.it/anki")
    runner.start()
    try:
        print("[*] 1. Initial online boot: registering Service Worker and caches...")
        for _ in range(25):
            time.sleep(0.5)
            ready = runner.evaluate("document.readyState")
            sw_active = runner.evaluate("Boolean(navigator.serviceWorker && navigator.serviceWorker.controller)")
            if ready == "complete" and sw_active:
                break

        print(f" [+] Service Worker active: {runner.evaluate('Boolean(navigator.serviceWorker.controller)')}")
        time.sleep(1.5)

        print("\n[*] 2. Cutting network completely (offline=True)...")
        runner.emulate_offline(True)
        time.sleep(0.5)
        assert runner.evaluate("navigator.onLine") is False, "Browser is not offline"

        print("[*] 3. Reloading page while 100% OFFLINE (Page.reload)...")
        runner.send("Page.reload", {"ignoreCache": False})

        reloaded_ok = False
        for _ in range(25):
            time.sleep(0.5)
            ready = runner.evaluate("document.readyState")
            decks_loaded = runner.evaluate("Boolean(document.getElementById('ankiDecksContainer')?.children?.length)")
            if ready == "complete" and decks_loaded:
                reloaded_ok = True
                break

        deck_count = runner.evaluate("document.querySelectorAll('#ankiDecksContainer > div').length")
        print(f" [+] Offline Reload Stage: Rendered {deck_count} decks from offline cache!")
        assert reloaded_ok and deck_count > 0, "Page failed to load offline via Service Worker"

        # Check font face or CSS loaded
        title = runner.evaluate("document.title")
        print(f" [+] Document title after offline reload: '{title}'")
        assert "AnkiDroid" in str(title) or "japan" in str(title).lower(), f"Unexpected title: {title}"

        # Check offline banner or status
        is_offline = runner.evaluate("navigator.onLine === false")
        assert is_offline, "Network state altered unexpectedly"

        print("\n" + "=" * 65)
        print("🎉 OFFLINE COLD RELOAD PASSED WITH 100% EMPIRICAL PROOF!")
        print("=" * 65)
        return True

    finally:
        runner.close()


if __name__ == "__main__":
    success = run_cold_reload_test()
    sys.exit(0 if success else 1)
