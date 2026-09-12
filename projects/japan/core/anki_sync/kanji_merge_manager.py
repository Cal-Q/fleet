"""Manages merging single-kanji cards between Kanji Image Deck and Vocab deck.

Handles schema updates (Image field on KanjiToKana), initial SRS migration
(preserving Image deck interval/reps), and lookup helpers for kanji images.
"""

from __future__ import annotations

import os
import sqlite3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import anki.collection
    from .anki_deck_manager import AnkiDeckManager

DECK_KANJI_IMAGE = "[JAP]::[TRAVEL]::Kanji - Image Deck"
DECK_VOCAB = "[JAP]::[TRAVEL]::Japanese -> Phonetic + Meaning"
MODEL_VOCAB = "KanjiToKana"


def ensure_model_schema(col: anki.collection.Collection) -> bool:
    """Ensures KanjiToKana model has Image field and template renders it."""
    model = col.models.by_name(MODEL_VOCAB)
    if not model:
        return False

    changed = False
    field_names = [f["name"] for f in model["flds"]]
    if "Image" not in field_names:
        new_fld = col.models.new_field("Image")
        col.models.add_field(model, new_fld)
        changed = True

    for tmpl in model.get("tmpls", []):
        afmt = tmpl.get("afmt", "")
        if "{{#Image}}" not in afmt and "{{Image}}" not in afmt:
            tmpl["afmt"] = afmt + "\n\n{{#Image}}\n{{Image}}\n{{/Image}}"
            changed = True

    if changed:
        col.models.save(model)
    return changed


def get_kanji_images(conn_or_path: sqlite3.Connection | str) -> dict[str, str]:
    """Returns mapping from kanji character to its HTML image tag."""
    if isinstance(conn_or_path, str):
        if not os.path.isfile(conn_or_path):
            return {}
        conn = sqlite3.connect(conn_or_path)
        should_close = True
    else:
        conn = conn_or_path
        should_close = False
    try:
        cur = conn.cursor()
        cur.execute("SELECT kanji, image FROM source_kanji_images")
        return {row[0].strip()[0]: row[1] for row in cur.fetchall() if row[0].strip()}
    finally:
        if should_close:
            conn.close()


def migrate_initial_overlapping_cards(col: anki.collection.Collection) -> int:
    """Migrates existing overlapping cards from Image deck to Vocab deck.
    Preserves SRS scheduling stats from Image deck and deletes duplicate note.
    """
    ensure_model_schema(col)

    did_img = col.decks.id(DECK_KANJI_IMAGE)
    did_voc = col.decks.id(DECK_VOCAB)
    if not did_img or not did_voc:
        return 0

    cids_img = col.decks.cids(did_img)
    cids_voc = col.decks.cids(did_voc)

    img_cards = {}
    for cid in cids_img:
        card = col.get_card(cid)
        k = card.note()["Kanji"].strip()
        if k:
            img_cards[k[0]] = card

    voc_cards = {}
    for cid in cids_voc:
        card = col.get_card(cid)
        f = card.note()["Form"].strip()
        if f and len(f) == 1:
            voc_cards[f[0]] = card

    overlap = set(img_cards.keys()) & set(voc_cards.keys())
    if not overlap:
        return 0

    notes_to_delete = []
    migrated = 0

    for k in overlap:
        c_img = img_cards[k]
        c_voc = voc_cards[k]
        n_img = c_img.note()
        n_voc = c_voc.note()

        # Populate Image field on vocab note
        n_voc["Image"] = n_img["Image"]
        col.update_note(n_voc)

        # Transfer SRS scheduling from Image card
        c_voc.ivl = c_img.ivl
        c_voc.due = c_img.due
        c_voc.factor = c_img.factor
        c_voc.reps = c_img.reps
        c_voc.lapses = c_img.lapses
        c_voc.type = c_img.type
        c_voc.queue = c_img.queue
        col.update_card(c_voc)

        notes_to_delete.append(n_img.id)
        migrated += 1

    if notes_to_delete:
        col.remove_notes(notes_to_delete)

    return migrated


def get_all_studied_kanji(deck_manager: AnkiDeckManager) -> set[str]:
    """Collects studied kanji from both Kanji - Image Deck and Vocab deck."""
    studied: set[str] = set()

    _, kanji_deck = deck_manager.try_get_deck(DECK_KANJI_IMAGE)
    if kanji_deck:
        for c in kanji_deck:
            if c.reps > 0 and "Kanji" in c.note.fields:
                val = c.note.fields["Kanji"].strip()
                if val:
                    studied.add(val[0])

    _, vocab_deck = deck_manager.try_get_deck(DECK_VOCAB)
    if vocab_deck:
        for c in vocab_deck:
            if c.reps > 0 and "Form" in c.note.fields:
                val = c.note.fields["Form"].strip()
                if len(val) == 1 and deck_manager.is_allowed_kanji_character(val[0]):
                    studied.add(val[0])

    return studied
