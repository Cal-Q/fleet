"""Processes sentences queued by the Bunpro Tampermonkey script and injects them into Anki."""

from __future__ import annotations

import concurrent.futures
import json
import os
import urllib.request
from typing import Any

from .anki_deck_manager import AnkiDeckManager
from .anki_direct_writer import sync_decks_batch
from .models import AddOrUpdateInfo

PENDING_SENTENCES_PATH = "/opt/japan/data/bunpro_sentences_pending.json"


def _read_json(path: str) -> list[dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _write_json(path: str, data: list[dict[str, Any]]) -> None:
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def _download_single_audio(url: str, dest_path: str) -> None:
    if os.path.exists(dest_path):
        return
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp, open(dest_path, "wb") as out:
            out.write(resp.read())
    except Exception as e:
        print(f"Failed to download audio for {os.path.basename(dest_path)}: {e}")


def apply_pending_sentences(collection_path: str, deck_manager: AnkiDeckManager) -> int:
    pending_notes = _read_json(PENDING_SENTENCES_PATH)
    if not pending_notes:
        return 0

    media_dir = os.path.join(os.path.dirname(collection_path), "collection.media")
    os.makedirs(media_dir, exist_ok=True)

    downloads_to_run: list[tuple[str, str]] = []
    deck_updates: dict[tuple[str, str, str], list[AddOrUpdateInfo]] = {}
    changed = 0

    for note in pending_notes:
        deck_name = note.get("deckName", "[JAP]::[TRAVEL]::[1] Jap Sentences")
        model_name = note.get("modelName", "Jap Sentences")
        main_field = note.get("mainField", "Japanese")
        fields = note.get("fields", {})
        audio_info = note.get("audio", [])

        for audio in audio_info:
            url = audio.get("url")
            filename = audio.get("filename")
            target_fields = audio.get("fields", [])

            if url and filename:
                media_path = os.path.join(media_dir, filename)
                downloads_to_run.append((url, media_path))
                for target_field in target_fields:
                    tag = f"[sound:{filename}]"
                    if target_field in fields:
                        fields[target_field] += tag
                    else:
                        fields[target_field] = tag

        key = (deck_name, model_name, main_field)
        if key not in deck_updates:
            deck_updates[key] = []
        deck_updates[key].append(AddOrUpdateInfo(fields))
        changed += 1

    if downloads_to_run:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(_download_single_audio, url, path) for url, path in downloads_to_run]
            concurrent.futures.wait(futures, timeout=15)

    specs = [
        (d_name, m_name, mf_name, updates, False)
        for (d_name, m_name, mf_name), updates in deck_updates.items()
        if updates
    ]
    if specs:
        sync_decks_batch(collection_path, specs)

    _write_json(PENDING_SENTENCES_PATH, [])
    return changed
