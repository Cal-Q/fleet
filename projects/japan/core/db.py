#!/usr/bin/env python3
"""
core/db.py — Local SQLite Database Connections
Provides thread-safe connections to collection.anki2 and dict_index.sqlite3.
Strictly <= 200 lines invariant.
"""

import os
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
    return ANKI_COLLECTION_PATH


def get_dict_db_path() -> str:
    return DICT_INDEX_PATH


def open_anki_db(timeout: float = 10.0) -> sqlite3.Connection:
    conn = sqlite3.connect(ANKI_COLLECTION_PATH, timeout=timeout)
    conn.create_collation("unicase", unicase_collation)
    return conn


def open_dict_db(timeout: float = 15.0) -> sqlite3.Connection:
    conn = sqlite3.connect(DICT_INDEX_PATH, timeout=timeout)
    conn.row_factory = sqlite3.Row
    return conn
