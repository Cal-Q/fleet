"""Headless entry point: initialize everything and run the deck-update pipeline once."""

from __future__ import annotations

import json
import os
import sys
import time

from .anki_deck_manager import AnkiDeckManager
from .bunpro_sentences import apply_pending_sentences
from .bunpro_vocab import apply_pending_vocab
from .dictionary_explorer import DictionaryExplorer
from .kanji_merge_manager import get_all_studied_kanji
from .local_files_manager import LocalFilesManager
from .pipeline import execute_updates, get_decks


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    start = time.monotonic()
    try:
        print("=== STARTED ===")
        local_files = LocalFilesManager(base_dir)
        collection_path = local_files.get_anki_collection_path()

        t0 = time.monotonic()
        deck_manager = AnkiDeckManager(collection_path)
        deck_manager.initialize()
        print(f"Anki Init: {(time.monotonic() - t0) * 1000:.0f} ms")

        vocab_changed = apply_pending_vocab(collection_path, deck_manager)
        sentences_changed = apply_pending_sentences(collection_path, deck_manager)
        if vocab_changed or sentences_changed:
            if vocab_changed:
                print(f"Bunpro vocab: merged {vocab_changed} queued entries")
            if sentences_changed:
                print(f"Bunpro sentences: merged {sentences_changed} queued entries")
            deck_manager.initialize()

        state_file = os.path.join(base_dir, "data", "pipeline_state.json")
        last_state = {}
        if os.path.isfile(state_file):
            try:
                with open(state_file, "r") as f:
                    last_state = json.load(f)
            except Exception:
                pass

        studied_kanji = get_all_studied_kanji(deck_manager)
        studied_count = len(studied_kanji)

        if (
            not vocab_changed
            and not sentences_changed
            and last_state.get("studied_count") == studied_count
        ):
            print("No vocabulary or kanji changes detected — skipping deck regeneration.")
            print(f"=== DONE! Total time: {(time.monotonic() - start) * 1000:.0f} ms ===")
            return 0

        t0 = time.monotonic()
        dictionary_explorer = DictionaryExplorer(local_files)
        dictionary_explorer.initialize()
        source_vocab_count = len(dictionary_explorer.get_source_english_to_kana())
        print(f"Dict Init: {(time.monotonic() - t0) * 1000:.0f} ms")

        t0 = time.monotonic()
        decks = get_decks(deck_manager, dictionary_explorer)
        print(f"Logic Calculation (get_decks): {(time.monotonic() - t0) * 1000:.0f} ms")

        t0 = time.monotonic()
        execute_updates(collection_path, decks)
        print(f"Anki Updates: {(time.monotonic() - t0) * 1000:.0f} ms")

        try:
            with open(state_file, "w") as f:
                json.dump({"studied_count": studied_count, "vocab_total": source_vocab_count}, f)
        except Exception:
            pass

        print(f"=== DONE! Total time: {(time.monotonic() - start) * 1000:.0f} ms ===")
        return 0
    except Exception as ex:
        import traceback
        traceback.print_exc()
        print(f"=== FAILED after {(time.monotonic() - start) * 1000:.0f} ms: {ex!r} ===", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
