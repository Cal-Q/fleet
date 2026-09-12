"""SQL helpers and lookup functions for anki_direct_writer."""

from __future__ import annotations

import hashlib
import json
import random
import sqlite3
import string
import time

_GUID_CHARS = string.ascii_uppercase + string.ascii_lowercase + string.digits


def generate_guid() -> str:
    return "".join(random.choice(_GUID_CHARS) for _ in range(10))


def get_checksum(field: str) -> int:
    if not field:
        return 0
    digest = hashlib.sha1(field.encode("utf-8")).digest()
    return (digest[0] << 24) | (digest[1] << 16) | (digest[2] << 8) | digest[3]


def get_max_due(conn: sqlite3.Connection) -> int:
    result = conn.execute("SELECT MAX(due) FROM cards WHERE type = 0").fetchone()
    return result[0] if (result and result[0] is not None) else 0


def smart_match(candidates: dict[str, int], target_name: str) -> int:
    for db_name, val in candidates.items():
        if db_name == target_name or db_name.replace("\x1f", "::") == target_name:
            return val
    for db_name, val in candidates.items():
        if db_name.lower() == target_name.lower() or db_name.replace("\x1f", "::").lower() == target_name.lower():
            return val
    for db_name, val in candidates.items():
        if db_name.strip() == target_name.strip() or db_name.replace("\x1f", "::").strip() == target_name.strip():
            return val
    return -1


def get_deck_id(conn: sqlite3.Connection, target_name: str) -> int:
    candidates: dict[str, int] = {}
    try:
        for name, deck_id in conn.execute("SELECT name, id FROM decks"):
            candidates[name] = deck_id
    except sqlite3.Error:
        row = conn.execute("SELECT decks FROM col").fetchone()
        if row and row[0]:
            try:
                for did, deck in json.loads(row[0]).items():
                    if deck.get("name") is not None:
                        candidates[deck["name"]] = int(did)
            except (ValueError, AttributeError):
                pass
    return smart_match(candidates, target_name)


def create_deck(conn: sqlite3.Connection, deck_name: str) -> int:
    deck_id = int(time.time() * 1000)
    now = int(time.time())
    sql_name = deck_name.replace("::", "\x1f")
    row = conn.execute("SELECT common, kind FROM decks LIMIT 1").fetchone()
    common = row[0] if row else b"\x08\x01\x10\x01\x18\xec\x04\x28\x4f\x38\xc1\xb4\x84\x01"
    kind = row[1] if row else b"\x0a\x09\x08\xa0\xf1\x93\x91\xcc\x33\x10\x32"
    conn.execute(
        "INSERT INTO decks (id, name, mtime_secs, usn, common, kind) VALUES (?, ?, ?, -1, ?, ?)",
        (deck_id, sql_name, now, common, kind),
    )
    return deck_id


def get_model_info(conn: sqlite3.Connection, target_name: str) -> tuple[int, dict[str, int]]:
    candidates: dict[str, int] = {}
    try:
        for name, model_id in conn.execute("SELECT name, id FROM notetypes"):
            candidates[name] = model_id
    except sqlite3.Error:
        row = conn.execute("SELECT models FROM col").fetchone()
        if row and row[0]:
            try:
                for mid, model in json.loads(row[0]).items():
                    if model.get("name") is not None:
                        candidates[model["name"]] = int(mid)
            except (ValueError, AttributeError):
                pass

    found_id = smart_match(candidates, target_name)
    if found_id == -1:
        return -1, {}

    field_map: dict[str, int] = {}
    try:
        for name, ord_ in conn.execute("SELECT name, ord FROM fields WHERE ntid = ? ORDER BY ord", (found_id,)):
            field_map[name] = ord_
        if field_map:
            return found_id, field_map
    except sqlite3.Error:
        pass

    row = conn.execute("SELECT models FROM col").fetchone()
    if row and row[0]:
        try:
            model = json.loads(row[0]).get(str(found_id))
            if model:
                for f in model.get("flds", []):
                    field_map[f["name"]] = f["ord"]
        except (ValueError, AttributeError, KeyError):
            pass
    return found_id, field_map


def update_note_sql(conn: sqlite3.Connection, note_id: int, fields: list[str], mod_time: int) -> None:
    flat_fields = "\x1f".join(fields)
    csum = get_checksum(fields[0] if fields else "")
    conn.execute(
        "UPDATE notes SET flds = ?, mod = ?, usn = -1, csum = ? WHERE id = ?",
        (flat_fields, mod_time, csum, note_id),
    )


def add_note_sql(
    conn: sqlite3.Connection, deck_id: int, model_id: int, fields: list[str], mod_time: int, due: int
) -> None:
    note_id = int(time.time() * 1000)
    time.sleep(0.001)
    flat_fields = "\x1f".join(fields)
    guid = generate_guid()
    csum = get_checksum(fields[0] if fields else "")
    sort_field = fields[0] if fields else ""
    conn.execute(
        "INSERT INTO notes (id, guid, mid, mod, usn, tags, flds, sfld, csum, flags, data) "
        "VALUES (?, ?, ?, ?, -1, '', ?, ?, ?, 0, '')",
        (note_id, guid, model_id, mod_time, flat_fields, sort_field, csum),
    )
    conn.execute(
        "INSERT INTO cards (nid, did, ord, mod, usn, type, queue, due, ivl, factor, reps, lapses, left, odue, odid, flags, data) "
        "VALUES (?, ?, 0, ?, -1, 0, 0, ?, 0, 0, 0, 0, 0, 0, 0, 0, '')",
        (note_id, deck_id, mod_time, due),
    )


def delete_notes_sql(conn: sqlite3.Connection, note_ids: list[int]) -> None:
    if not note_ids:
        return
    placeholders = ",".join("?" for _ in note_ids)
    card_ids = [r[0] for r in conn.execute(f"SELECT id FROM cards WHERE nid IN ({placeholders})", note_ids)]
    for cid in card_ids:
        conn.execute("INSERT OR REPLACE INTO graves (usn, oid, type) VALUES (-1, ?, 0)", (cid,))
    for nid in note_ids:
        conn.execute("INSERT OR REPLACE INTO graves (usn, oid, type) VALUES (-1, ?, 1)", (nid,))
    conn.execute(f"DELETE FROM cards WHERE nid IN ({placeholders})", note_ids)
    conn.execute(f"DELETE FROM notes WHERE id IN ({placeholders})", note_ids)


def reset_card_reps(conn: sqlite3.Connection, note_id: int, mod_time: int, new_due: int) -> None:
    """Resets repetition count, interval, and learning queue on a newly merged card."""
    conn.execute(
        "UPDATE cards SET reps = 0, ivl = 0, factor = 2500, type = 0, queue = 0, "
        "lapses = 0, left = 0, odue = 0, due = ?, mod = ?, usn = -1 WHERE nid = ?",
        (new_due, mod_time, note_id),
    )


def batch_remove_kanji_from_image_deck(conn: sqlite3.Connection, kanji_chars: set[str]) -> None:
    """Removes duplicate cards for kanji_chars from Kanji - Image Deck in 1 batch query."""
    if not kanji_chars:
        return
    deck_id = get_deck_id(conn, "[JAP]::[TRAVEL]::Kanji - Image Deck")
    if deck_id == -1:
        return
    rows = conn.execute(
        "SELECT n.id, n.flds FROM notes n JOIN cards c ON c.nid = n.id WHERE c.did = ?",
        (deck_id,),
    ).fetchall()
    notes_to_delete = [
        nid for nid, flds in rows
        if flds.split("\x1f")[0].strip() in kanji_chars
    ]
    if notes_to_delete:
        delete_notes_sql(conn, notes_to_delete)
