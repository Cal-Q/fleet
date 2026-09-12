"""Merges vocab queued by the Bunpro Tampermonkey script into the SQLite dict_index database."""

from __future__ import annotations

import json
import os
import sqlite3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .anki_deck_manager import AnkiDeckManager

PENDING_PATH = "/opt/japan/data/bunpro_vocab_pending.json"
KNOWN_PATH = "/opt/japan/data/bunpro_vocab_known.json"
DICT_INDEX_PATH = "/opt/japan/data/dict_index.sqlite3"


def _read_json(path: str) -> dict[str, str]:
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write_json(path: str, data: dict[str, str]) -> None:
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def apply_pending_vocab(
    collection_path: str = "",
    deck_manager: AnkiDeckManager | None = None,
    db_path: str = DICT_INDEX_PATH,
) -> int:
    pending = _read_json(PENDING_PATH)
    if not pending and os.path.isfile(KNOWN_PATH):
        return 0

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT english, kana FROM source_english_to_kana ORDER BY id ASC")
    existing_rows = cur.fetchall()
    existing_map: dict[str, str] = {eng: kana for eng, kana in existing_rows}

    changed = 0
    if pending:
        for front, back in pending.items():
            if front not in existing_map:
                cur.execute("INSERT INTO source_english_to_kana (english, kana) VALUES (?, ?)", (front, back))
                existing_map[front] = back
                changed += 1
            elif existing_map[front] != back:
                cur.execute("UPDATE source_english_to_kana SET kana = ? WHERE english = ?", (back, front))
                existing_map[front] = back
                changed += 1
        conn.commit()

    conn.close()

    if pending or not os.path.isfile(KNOWN_PATH):
        _write_json(KNOWN_PATH, existing_map)
    if pending:
        _write_json(PENDING_PATH, {})

    return changed
