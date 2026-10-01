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
from .kanji_merge_manager import (
    get_all_studied_kanji,
    normalize_media_svg_case,
    sync_bidirectional_kanji_in_anki,
)
from .local_files_manager import LocalFilesManager
from .pipeline import execute_updates, get_decks
from .restore_kanji_srs import restore_srs_state


def snapshot_database(file_path: str, max_backups: int = 10) -> str | None:
    """Takes a timestamped snapshot of a database file, keeping the latest N backups."""
    if not os.path.isfile(file_path):
        return None
    import glob, shutil
    ts = int(time.time())
    bak_path = f"{file_path}.auto_{ts}.bak"
    try:
        shutil.copy2(file_path, bak_path)
        existing = sorted(glob.glob(f"{file_path}.auto_*.bak"))
        if len(existing) > max_backups:
            for old in existing[:-max_backups]:
                try:
                    os.remove(old)
                except OSError:
                    pass
        return bak_path
    except Exception as e:
        print(f"Backup warning for {file_path}: {e}", file=sys.stderr)
        return None


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    start = time.monotonic()
    try:
        print("=== STARTED ===")
        local_files = LocalFilesManager(base_dir)
        collection_path = local_files.get_anki_collection_path()

        dict_path = os.path.join(os.path.dirname(local_files.get_jmdict_file_path()), "dict_index.sqlite3")
        if not os.path.isfile(dict_path):
            dict_path = os.path.join(os.path.dirname(base_dir), "data", "dict_index.sqlite3")

        col_bak = snapshot_database(collection_path)
        if col_bak:
            print(f"Pre-flight snapshot: {os.path.basename(col_bak)}")
        if os.path.isfile(dict_path):
            snapshot_database(dict_path)

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

        sync_stats = {}
        if os.path.isfile(dict_path):
            sync_stats = sync_bidirectional_kanji_in_anki(dict_path)
            if any(sync_stats.values()):
                print(f"Bidirectional in_anki synced: {sync_stats}")

        media_dir = os.path.join(os.path.dirname(collection_path), "collection.media")
        if os.path.isdir(media_dir):
            n_svg = normalize_media_svg_case(media_dir)
            if n_svg:
                print(f"Normalized {n_svg} SVG media case aliases")

        data_dir = os.path.dirname(dict_path)
        state_file = os.path.join(data_dir, "pipeline_state.json")
        last_state = {}
        if os.path.isfile(state_file):
            try:
                with open(state_file, "r") as f:
                    last_state = json.load(f)
            except Exception:
                pass

        studied_kanji = get_all_studied_kanji(deck_manager)
        studied_count = len(studied_kanji)
        in_anki_changed = any(sync_stats.values()) if sync_stats else False

        if (
            not vocab_changed
            and not sentences_changed
            and not in_anki_changed
            and last_state.get("studied_count") == studied_count
        ):
            print("No vocabulary or kanji changes detected — skipping deck regeneration.")
            print(f"=== DONE! Total time: {(time.monotonic() - start) * 1000:.0f} ms ===")
            return 0

        t0 = time.monotonic()
        dictionary_explorer = DictionaryExplorer(local_files)
        dictionary_explorer.initialize()
        source_vocab_count = dictionary_explorer.get_in_anki_entries_count()
        print(f"Dict Init: {(time.monotonic() - t0) * 1000:.0f} ms")

        t0 = time.monotonic()
        decks = get_decks(deck_manager, dictionary_explorer)
        print(f"Logic Calculation (get_decks): {(time.monotonic() - t0) * 1000:.0f} ms")

        t0 = time.monotonic()
        execute_updates(collection_path, decks)
        print(f"Anki Updates: {(time.monotonic() - t0) * 1000:.0f} ms")

        t0 = time.monotonic()
        srs_res = restore_srs_state(collection_path)
        print(f"SRS State Restoration: {srs_res['restored']} cards restored in {(time.monotonic() - t0) * 1000:.0f} ms")

        staged_file = os.path.join(data_dir, "bunpro_vocab_staged.json")
        if os.path.isfile(staged_file):
            try:
                os.remove(staged_file)
            except Exception:
                pass

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
