#!/usr/bin/env python3
"""
core/anki_settings_store.py — Persistent Settings Store for AnkiWeb
Provides centralized loading and atomic writing of custom deck settings.
Strictly <= 200 lines invariant.
"""

import json
import os
from typing import Any, Dict

DEFAULT_SETTINGS: Dict[str, Any] = {
    "deck_timers": {},
    "timer_duration": 15,
    "session_target_min": 25,
    "furigana_mode": "unstudied",
    "front_font_size": 38,
    "back_font_size": 20,
    "collapsed_decks": []
}


def get_settings_file_path(workspace_dir: str) -> str:
    return os.path.join(workspace_dir, "data", "anki_settings.json")


def get_persisted_settings(workspace_dir: str) -> Dict[str, Any]:
    fpath = get_settings_file_path(workspace_dir)
    settings = dict(DEFAULT_SETTINGS)
    if os.path.exists(fpath):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    settings.update(data)
        except Exception:
            pass
    return settings


def save_persisted_settings(workspace_dir: str, settings: Dict[str, Any]) -> bool:
    fpath = get_settings_file_path(workspace_dir)
    try:
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        tmp_path = fpath + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, fpath)
        return True
    except Exception:
        return False
