"""Writes straight into live collection.anki2 via raw SQL."""

from __future__ import annotations

import re
import sqlite3
import time

from .anki_direct_writer_helpers import (
    create_deck,
    delete_notes_sql,
    generate_guid,
    get_checksum,
    get_deck_id,
    get_max_due,
    get_model_info,
    reset_card_reps,
)
from .models import AddOrUpdateInfo


def strip_ruby(text: str) -> str:
    return re.sub(r"<.*?>", "", re.sub(r"<rt>.*?</rt>", "", text)).strip()


def _sync_single_deck_conn(
    conn: sqlite3.Connection,
    deck_name: str,
    model_name: str,
    main_field_name: str,
    incoming_data: list[AddOrUpdateInfo],
    allow_delete: bool = True,
    allow_add: bool = True,
    allowed_add_words: set[str] | None = None,
) -> None:
    deck_id = get_deck_id(conn, deck_name)
    if deck_id == -1:
        deck_id = create_deck(conn, deck_name)

    model_id, field_map = get_model_info(conn, model_name)
    if model_id == -1:
        raise ValueError(f"Model '{model_name}' not found! Check the name exactly.")

    if main_field_name not in field_map:
        raise ValueError(f"Field '{main_field_name}' does not exist in Model '{model_name}'.")

    main_field_index = field_map[main_field_name]
    existing_notes_by_id: dict[int, list[str]] = {}
    existing_key_to_id: dict[str, int] = {}

    rows = conn.execute(
        "SELECT n.id, n.flds FROM notes n JOIN cards c ON c.nid = n.id WHERE c.did = ?",
        (deck_id,),
    ).fetchall()

    for note_id, flds in rows:
        split = flds.split("\x1f")
        if len(split) > main_field_index:
            existing_notes_by_id[note_id] = split
            raw_key = split[main_field_index]
            clean_k = strip_ruby(raw_key)
            if raw_key not in existing_key_to_id:
                existing_key_to_id[raw_key] = note_id
            if clean_k not in existing_key_to_id:
                existing_key_to_id[clean_k] = note_id

    now = int(time.time())
    matched_note_ids: set[int] = set()
    current_due = get_max_due(conn)

    notes_to_update: list[tuple[str, int, int, int]] = []
    notes_to_add: list[tuple[int, str, int, int, str, str, int]] = []
    cards_to_add: list[tuple[int, int, int, int]] = []

    cur_res = conn.execute("SELECT coalesce(max(id), 0) FROM notes").fetchone()
    next_note_id = max(int(time.time() * 1000), cur_res[0] if cur_res else 0)

    for info in incoming_data:
        key = info.fields_and_values.get(main_field_name)
        if key is None:
            continue

        img_val = info.fields_and_values.get("Image", "")
        clean_key = strip_ruby(key)
        matched_id = existing_key_to_id.get(key) or existing_key_to_id.get(clean_key)

        if matched_id and matched_id in existing_notes_by_id:
            matched_note_ids.add(matched_id)
            current_fields = list(existing_notes_by_id[matched_id])
            changed = False
            for field_name, value in info.fields_and_values.items():
                idx = field_map.get(field_name)
                if idx is None:
                    continue
                if idx >= len(current_fields):
                    current_fields.extend([""] * (idx + 1 - len(current_fields)))
                if current_fields[idx] != value:
                    current_fields[idx] = value
                    changed = True

            if changed:
                flat_fields = "\x1f".join(current_fields)
                csum = get_checksum(current_fields[0] if current_fields else "")
                notes_to_update.append((flat_fields, now, csum, matched_id))
        elif allow_add:
            if allowed_add_words is not None:
                meaning_val = info.fields_and_values.get("Meaning", "")
                kana_val = meaning_val.split("<br>")[0].strip() if meaning_val else ""
                if clean_key not in allowed_add_words and key not in allowed_add_words and kana_val not in allowed_add_words:
                    continue

            max_index = max(field_map.values())
            new_fields = [""] * (max_index + 1)
            for field_name, value in info.fields_and_values.items():
                idx = field_map.get(field_name)
                if idx is not None:
                    new_fields[idx] = value

            next_note_id += 1
            note_id = next_note_id
            current_due += 1
            flat_fields = "\x1f".join(new_fields)
            guid = generate_guid()
            csum = get_checksum(new_fields[0] if new_fields else "")
            sort_field = new_fields[0] if new_fields else ""

            notes_to_add.append((note_id, guid, model_id, now, flat_fields, sort_field, csum))
            cards_to_add.append((note_id, deck_id, now, current_due))

    if notes_to_update:
        conn.executemany("UPDATE notes SET flds = ?, mod = ?, usn = -1, csum = ? WHERE id = ?", notes_to_update)

    if notes_to_add:
        conn.executemany(
            "INSERT INTO notes (id, guid, mid, mod, usn, tags, flds, sfld, csum, flags, data) "
            "VALUES (?, ?, ?, ?, -1, '', ?, ?, ?, 0, '')",
            notes_to_add,
        )
        conn.executemany(
            "INSERT INTO cards (nid, did, ord, mod, usn, type, queue, due, ivl, factor, reps, lapses, left, odue, odid, flags, data) "
            "VALUES (?, ?, 0, ?, -1, 0, 0, ?, 0, 0, 0, 0, 0, 0, 0, 0, '')",
            cards_to_add,
        )

    if allow_delete:
        ids_to_delete = [nid for nid in existing_notes_by_id if nid not in matched_note_ids]
        if ids_to_delete:
            delete_notes_sql(conn, ids_to_delete)


def sync_decks_batch(
    collection_path: str,
    deck_sync_specs: list[tuple[str, str, str, list[AddOrUpdateInfo], bool]],
) -> None:
    conn = sqlite3.connect(collection_path, isolation_level=None, timeout=30)
    conn.create_collation("unicase", lambda a, b: (a.casefold() > b.casefold()) - (a.casefold() < b.casefold()))
    conn.execute("PRAGMA cache_size = -64000")
    try:
        conn.execute("BEGIN")
        try:
            for spec in deck_sync_specs:
                deck_name, model_name, main_field_name, incoming_data = spec[0], spec[1], spec[2], spec[3]
                allow_delete = spec[4] if len(spec) > 4 else True
                allow_add = spec[5] if len(spec) > 5 else True
                allowed_add_words = spec[6] if len(spec) > 6 else None
                _sync_single_deck_conn(conn, deck_name, model_name, main_field_name, incoming_data, allow_delete, allow_add, allowed_add_words)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()


def sync_deck_sql(
    collection_path: str,
    deck_name: str,
    model_name: str,
    main_field_name: str,
    incoming_data: list[AddOrUpdateInfo],
    allow_delete: bool = True,
) -> None:
    sync_decks_batch(collection_path, [(deck_name, model_name, main_field_name, incoming_data, allow_delete)])
