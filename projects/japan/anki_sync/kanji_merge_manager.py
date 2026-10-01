"""Manages merging single-kanji cards between Kanji Image Deck and Vocab deck.

Handles bidirectional in_anki consistency, SRS metrics consolidation,
media uppercase hardlinking, and kanji image lookups.
Strictly <= 200 lines invariant.
"""

from __future__ import annotations

import glob
import os
import sqlite3
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .anki_deck_manager import AnkiDeckManager

DECK_KANJI_IMAGE = "[JAP]::[TRAVEL]::Kanji - Image Deck"
DECK_VOCAB = "[JAP]::[TRAVEL]::Japanese -> Phonetic + Meaning"


def get_kanji_images(conn_or_path: sqlite3.Connection | str) -> dict[str, str]:
    """Returns mapping from kanji character to its HTML image tag."""
    conn = sqlite3.connect(conn_or_path) if isinstance(conn_or_path, str) else conn_or_path
    should_close = isinstance(conn_or_path, str)
    try:
        cur = conn.cursor()
        cur.execute("SELECT kanji, image FROM source_kanji_images")
        return {r[0].strip()[0]: r[1] for r in cur.fetchall() if r[0].strip()}
    finally:
        if should_close:
            conn.close()


def sync_bidirectional_kanji_in_anki(conn_or_path: sqlite3.Connection | str) -> dict[str, int]:
    """Propagates single-kanji in_anki = 1 from master kanji_catalog to jlpt_vocab."""
    conn = sqlite3.connect(conn_or_path) if isinstance(conn_or_path, str) else conn_or_path
    should_close = isinstance(conn_or_path, str)
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE jlpt_vocab SET in_anki = 1
            WHERE word IN (SELECT kanji FROM kanji_catalog WHERE in_anki = 1)
              AND length(word) = 1 AND in_anki = 0
        """)
        jv = cur.rowcount

        conn.commit()
        return {"jlpt_from_kc": jv}
    finally:
        if should_close:
            conn.close()


def merge_vocab_srs_to_image_deck(col_path: str) -> int:
    """Consolidates SRS scheduling & revlog from single-kanji Vocab cards into Image Deck."""
    if not os.path.isfile(col_path):
        return 0
    conn = sqlite3.connect(col_path)
    conn.create_collation("unicase", lambda a, b: (a.casefold() > b.casefold()) - (a.casefold() < b.casefold()))
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM decks WHERE name IN (?, ?)",
                    (DECK_VOCAB.replace("::", "\x1f"), DECK_KANJI_IMAGE.replace("::", "\x1f")))
        dmap = {r[1]: r[0] for r in cur.fetchall()}
        did_voc, did_img = dmap.get(DECK_VOCAB.replace("::", "\x1f")), dmap.get(DECK_KANJI_IMAGE.replace("::", "\x1f"))
        if not did_voc or not did_img:
            return 0

        cur.execute("SELECT c.id, n.flds, c.type, c.queue, c.due, c.ivl, c.factor, c.reps, c.lapses, c.data FROM notes n JOIN cards c ON c.nid = n.id WHERE c.did = ?", (did_voc,))
        voc_cards = {}
        for r in cur.fetchall():
            k = r[1].split("\x1f")[0].strip()
            if len(k) == 1:
                voc_cards[k] = (r[0], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9])

        cur.execute("SELECT c.id, n.flds, c.ivl, c.reps FROM notes n JOIN cards c ON c.nid = n.id WHERE c.did = ?", (did_img,))
        img_cards = {}
        for r in cur.fetchall():
            k = r[1].split("\x1f")[0].strip()
            if len(k) == 1:
                img_cards[k] = (r[0], r[2], r[3])

        merged = 0
        now_ts = int(time.time())
        for k, voc in voc_cards.items():
            if k not in img_cards:
                continue
            voc_cid, v_type, v_queue, v_due, v_ivl, v_factor, v_reps, v_lapses, v_data = voc
            img_cid, i_ivl, i_reps = img_cards[k]
            if (v_ivl or 0) > (i_ivl or 0) or (i_reps or 0) == 0:
                cur.execute("""UPDATE cards SET type=?, queue=?, due=?, ivl=?, factor=?, reps=?, lapses=?, data=?, mod=? WHERE id=?""",
                            (v_type, v_queue, v_due, max(v_ivl or 0, i_ivl or 0), v_factor, max(v_reps or 0, i_reps or 0), max(v_lapses or 0, 0), v_data, now_ts, img_cid))
                merged += 1
            cur.execute("UPDATE revlog SET cid = ? WHERE cid = ?", (img_cid, voc_cid))
        conn.commit()
        return merged
    finally:
        conn.close()


def normalize_media_svg_case(media_dir: str) -> int:
    """Ensures uppercase hex hardlinks exist for all 0*.svg files."""
    if not os.path.isdir(media_dir):
        return 0
    created = 0
    for p in glob.glob(os.path.join(media_dir, "0*.svg")):
        fname = os.path.basename(p)
        if fname.endswith(".svg"):
            prefix = fname[:-4]
            upper_prefix = prefix.upper()
            if prefix != upper_prefix:
                dst = os.path.join(media_dir, upper_prefix + ".svg")
                if not os.path.exists(dst):
                    try:
                        os.link(p, dst)
                        created += 1
                    except OSError:
                        pass
    return created


def get_all_studied_kanji(deck_manager: AnkiDeckManager) -> set[str]:
    """Collects studied kanji from kanji_catalog with in_anki = 1."""
    try:
        lf = getattr(deck_manager, "_local_files", None)
        dict_path = os.path.join(os.path.dirname(lf.get_jmdict_file_path()), "dict_index.sqlite3") if lf else ""
        if not os.path.isfile(dict_path):
            dict_path = "/opt/japan/data/dict_index.sqlite3"
        if os.path.isfile(dict_path):
            with sqlite3.connect(dict_path) as conn:
                res = {r[0] for r in conn.execute("SELECT kanji FROM kanji_catalog WHERE in_anki = 1") if r[0]}
                if res:
                    return res
    except Exception:
        pass
    studied: set[str] = set()
    _, kanji_deck = deck_manager.try_get_deck(DECK_KANJI_IMAGE)
    if kanji_deck:
        for c in kanji_deck:
            if c.reps > 1 and "Kanji" in c.note.fields:
                val = c.note.fields["Kanji"].strip()
                if val:
                    studied.add(val[0])
    return studied
