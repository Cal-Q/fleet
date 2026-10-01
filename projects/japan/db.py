#!/usr/bin/env python3
"""
core/db.py — Local SQLite Database Connections
Provides thread-safe connections to collection.anki2 and dict_index.sqlite3.
Strictly <= 200 lines invariant.
"""

import os
import re
import sqlite3

BASE_DIR = "/opt/japan"
ANKI_COLLECTION_PATH = os.path.join(BASE_DIR, ".local/share/Anki2/User 1/collection.anki2")
DICT_INDEX_PATH = os.path.join(BASE_DIR, "data/dict_index.sqlite3")


def unicase_collation(a: str, b: str) -> int:
    a_low = a.lower()
    b_low = b.lower()
    if a_low > b_low:
        return 1
    elif a_low < b_low:
        return -1
    return 0


def get_anki_db_path() -> str:
    env_path = os.environ.get("ANKI_DB_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    candidates = [
        "/data/data/com.termux/files/home/japan/data/collection.anki2",
        "/data/data/com.termux/files/home/collection.anki2",
        os.path.expanduser("~/.local/share/Anki2/User 1/collection.anki2"),
        "/opt/japan/.local/share/Anki2/User 1/collection.anki2",
        "/mnt/workspaces/japan/.local/share/Anki2/User 1/collection.anki2",
        "/sdcard/AnkiDroid/collection.anki2",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return ANKI_COLLECTION_PATH


def get_dict_db_path() -> str:
    env_path = os.environ.get("DICT_DB_PATH")
    if env_path and os.path.exists(env_path) and os.path.getsize(env_path) > 1000:
        return env_path
    candidates = [
        "/data/data/com.termux/files/home/japan/data/furigana.sqlite3",
        "/data/data/com.termux/files/home/japan/data/dict_index.sqlite3",
        "/opt/japan/data/furigana.sqlite3",
        "/opt/japan/data/dict_index.sqlite3",
        "/mnt/workspaces/japan/data/furigana.sqlite3",
        "/mnt/workspaces/japan/data/dict_index.sqlite3",
        "/sdcard/AnkiDroid/furigana.sqlite3",
        "/sdcard/AnkiDroid/dict_index.sqlite3",
    ]
    for p in candidates:
        if os.path.exists(p) and os.path.getsize(p) > 1000:
            return p
    return DICT_INDEX_PATH


def open_anki_db(timeout: float = 10.0) -> sqlite3.Connection:
    conn = sqlite3.connect(get_anki_db_path(), timeout=timeout)
    conn.create_collation("unicase", unicase_collation)
    return conn


def open_dict_db(timeout: float = 15.0, read_only: bool = False) -> sqlite3.Connection:
    path = get_dict_db_path()
    if not os.path.exists(path):
        if read_only:
            conn = sqlite3.connect(":memory:", timeout=timeout)
        else:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            conn = sqlite3.connect(path, timeout=timeout)
    else:
        if read_only:
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=timeout)
        else:
            conn = sqlite3.connect(path, timeout=timeout)
    conn.row_factory = sqlite3.Row
    return conn


def clean_kana(furigana: str, word: str = "") -> str:
    if not furigana:
        return word
    text = re.sub(r'[\u4e00-\u9faf\u3400-\u4dbf々〆ヵヶ]+[（\(]([ぁ-んァ-ンー]+)[）\)]', r'\1', furigana)
    text = re.sub(r'[（\(]([ぁ-んァ-ンー]+)[）\)]', r'\1', text)
    return text.strip()

