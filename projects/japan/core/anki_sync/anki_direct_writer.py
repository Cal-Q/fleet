"""Writes straight into live collection.anki2 via raw SQL."""

from __future__ import annotations

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


def _sync_single_deck_conn(
    conn: sqlite3.Connection,
    deck_name: str,
    model_name: str,
    main_field_name: str,
    incoming_data: list[AddOrUpdateInfo],
    allow_delete: bool = True,
    allow_add: bool = True,
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
    existing_notes: dict[str, tuple[int, list[str]]] = {}

    rows = conn.execute(
        "SELECT n.id, n.flds FROM notes n JOIN cards c ON c.nid = n.id WHERE c.did = ?",
        (deck_id,),
    ).fetchall()

    for note_id, flds in rows:
        split = flds.split("\x1f")
        if len(split) > main_field_index:
            key = split[main_field_index]
            if key not in existing_notes:
                existing_notes[key] = (note_id, split)

    now = int(time.time())
    processed_keys: set[str] = set()
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

        processed_keys.add(key)
        img_val = info.fields_and_values.get("Image", "")

        if key in existing_notes:
            note_id, current_fields = existing_notes[key]
            current_fields = list(current_fields)
            changed = False

            image_idx = field_map.get("Image")
            if image_idx is not None and img_val:
                old_img = current_fields[image_idx] if image_idx < len(current_fields) else ""
                if not old_img and img_val:
                    current_due += 1
                    reset_card_reps(conn, note_id, now, current_due)

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
                notes_to_update.append((flat_fields, now, csum, note_id))
        elif allow_add:
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
        ids_to_delete = [note_id for key, (note_id, _) in existing_notes.items() if key not in processed_keys]
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
                _sync_single_deck_conn(conn, deck_name, model_name, main_field_name, incoming_data, allow_delete, allow_add)
            now_ms = int(time.time() * 1000)
            conn.execute("UPDATE col SET mod = ?", (now_ms,))
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
