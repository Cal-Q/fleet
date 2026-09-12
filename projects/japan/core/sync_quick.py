#!/usr/bin/env python3
"""Lightweight sync runner that checks for queued Bunpro sentences/vocab,
merges them into collection.anki2, regenerates decks, and pushes to AnkiWeb."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from anki_sync.anki_deck_manager import AnkiDeckManager
from anki_sync.bunpro_sentences import apply_pending_sentences
from anki_sync.bunpro_vocab import apply_pending_vocab
from anki_sync.local_files_manager import LocalFilesManager
from anki_sync.sync_helpers import anki_already_running
from sync_and_push import post_sync, pre_sync_and_leech_lifecycle, run_pipeline


def process_pending_and_sync() -> bool:
    if anki_already_running():
        return False

    base_dir = str(REPO_ROOT)
    local_files = LocalFilesManager(base_dir)
    collection_path = local_files.get_anki_collection_path()

    deck_manager = AnkiDeckManager(collection_path)
    deck_manager.initialize()

    vocab_changed = apply_pending_vocab(collection_path, deck_manager)
    sentences_changed = apply_pending_sentences(collection_path, deck_manager)

    if vocab_changed or sentences_changed:
        print(
            f"[sync_quick] Merged {vocab_changed} vocab, {sentences_changed} sentences. Regenerating decks and pushing..."
        )
        if run_pipeline():
            post_sync()
            return True
    return False


if __name__ == "__main__":
    process_pending_and_sync()
