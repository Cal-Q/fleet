"""Port of AnkiDirectReader.cs: reads every deck straight out of collection.anki2."""

from __future__ import annotations

import json
import os
import sqlite3

from .models import AnkiCard, AnkiNote


def read_all_decks(
    collection_path: str, decks_to_load: list[str] | None = None
) -> dict[str, list[AnkiCard]]:
    results: dict[str, list[AnkiCard]] = {}
    if not os.path.isfile(collection_path):
        return results

    conn = sqlite3.connect(collection_path, timeout=5)
    conn.create_collation(
        "unicase",
        lambda a, b: (a.casefold() > b.casefold()) - (a.casefold() < b.casefold()),
    )
    conn.execute("PRAGMA mmap_size = 268435456")
    conn.execute("PRAGMA cache_size = -64000")
    try:
        deck_map, model_map = _parse_collection_meta(conn)
        id_to_name = {did: name for name, did in deck_map.items()}

        target_names = (
            set(decks_to_load)
            if decks_to_load
            else {k for k in deck_map if "[IGNORE VSTUDIO]" not in k}
        )
        for name in target_names:
            results[name] = []

        target_dids = [did for name, did in deck_map.items() if name in target_names]
        if target_dids:
            placeholders = ",".join("?" for _ in target_dids)
            query = (
                f"SELECT c.id, c.nid, c.reps, n.mid, n.flds, c.did "
                f"FROM cards c JOIN notes n ON c.nid = n.id WHERE c.did IN ({placeholders})"
            )
            cursor = conn.execute(query, target_dids)
            for card_id, note_id, reps, model_id, raw_fields, did in cursor:
                deck_name = id_to_name.get(did)
                if deck_name in target_names:
                    note = AnkiNote(note_id=note_id)
                    field_names = model_map.get(model_id)
                    if field_names:
                        values = raw_fields.split("\x1f")
                        for name, value in zip(field_names, values):
                            note.fields[name] = value
                    results[deck_name].append(
                        AnkiCard(card_id=card_id, note_id=note_id, reps=reps, note=note)
                    )
    finally:
        conn.close()

    return results


def _parse_collection_meta(
    conn: sqlite3.Connection,
) -> tuple[dict[str, int], dict[int, list[str]]]:
    deck_map: dict[str, int] = {}
    model_map: dict[int, list[str]] = {}

    row = conn.execute("SELECT decks, models FROM col").fetchone()
    use_legacy_json = bool(row and row[0] and len(row[0]) > 2)

    if use_legacy_json:
        decks_json, models_json = row
        try:
            for did, deck in json.loads(decks_json).items():
                name = deck.get("name")
                if name is not None:
                    deck_map[name] = int(did)
        except (ValueError, AttributeError):
            pass

        try:
            for mid, model in json.loads(models_json).items():
                flds = model.get("flds")
                if flds is not None:
                    model_map[int(mid)] = [f["name"] for f in flds]
        except (ValueError, AttributeError, KeyError):
            pass
    else:
        try:
            for deck_id, name in conn.execute("SELECT id, name FROM decks"):
                deck_map[name] = deck_id

            model_ids = [r[0] for r in conn.execute("SELECT id FROM notetypes")]
            for model_id in model_ids:
                fields = [
                    r[0]
                    for r in conn.execute(
                        "SELECT name FROM fields WHERE ntid = ? ORDER BY ord", (model_id,)
                    )
                ]
                model_map[model_id] = fields
        except sqlite3.Error:
            pass

    return deck_map, model_map
