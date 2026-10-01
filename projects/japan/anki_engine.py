#!/usr/bin/env python3
"""
core/anki_engine.py — Core Anki Query & Extraction Engine
Pure Python standard library + sqlite3 with zero external dependencies.
Strictly <= 200 lines invariant.
"""

import time
from typing import Any, Dict, List
from core.db import open_anki_db, open_dict_db
from core.anki_sm2 import get_today_days, calculate_intervals_for_card
from core.anki_web_furigana import format_card_data, get_user_studied_kanji

DECK_META = {
    "[JAP]": ("Giapponese • Master Shuffle", "Master Deck", "🎲"),
    "[JAP]::[TRAVEL]": ("Giapponese • Travel Pack", "Raccolta", "📚"),
    "[JAP]::[TRAVEL]::Japanese -> Phonetic + Meaning": (
        "Vocabolario • Lettura & Significato", "Vocab", "語"
    ),
    "[JAP]::[TRAVEL]::Kanji - Image Deck": ("Kanji • Riconoscimento Visivo", "Kanji", "漢"),
    "[JAP]::Kanji -> Writing Practice": ("Kanji • Pratica di Scrittura", "Kanji", "✍️"),
    "[JAP]::[TRAVEL]::[1] Jap Sentences": ("Frasi • Comprensione Immersiva", "Frasi", "文"),
    "[1] Stuff I make": ("Contatori & Tabelle Create", "Master Deck", "🎲"),
    "[1] Stuff I make::Counters": ("Contatori Giapponesi", "Special", "🔢"),
    "Storia del Giappone": ("Storia del Giappone • Completo", "Master Deck", "🎲"),
    "Storia del Giappone::Modulo 1": ("Storia del Giappone • Modulo 1", "UniTO", "🏛️"),
    "Lingua Inglese": ("Lingua Inglese • Completo", "Master Deck", "🎲"),
    "Lingua Inglese::Linguistica": ("Lingua Inglese • Linguistica", "UniTO", "📖"),
    "[1] Letteratura per ragazzi": ("Letteratura per Ragazzi", "Letture", "📕"),
}


def parse_anki_flds(flds_raw: str) -> List[str]:
    return [f.strip() for f in flds_raw.split("\x1f")]


def get_deck_and_child_ids(cur, did: int) -> List[int]:
    cur.execute("SELECT id, name FROM decks WHERE id = ?", (did,))
    row = cur.fetchone()
    if not row:
        return [did]
    name = row[1]
    cur.execute("SELECT id FROM decks WHERE name = ? OR name LIKE ?", (name, name + "\x1f%"))
    return [r[0] for r in cur.fetchall()]


def fetch_anki_decks_data() -> Dict[str, Any]:
    conn = open_anki_db()
    cur = conn.cursor()
    today_days = get_today_days(cur)
    cur.execute("SELECT id, name FROM decks WHERE id != 1 ORDER BY name ASC")
    decks = cur.fetchall()
    cur.execute("""
        SELECT did,
            SUM(CASE WHEN queue = 0 THEN 1 ELSE 0 END) as new_c,
            SUM(CASE WHEN queue = 1 THEN 1 ELSE 0 END) as lrn_c,
            SUM(CASE WHEN queue = 2 AND due <= ? THEN 1 ELSE 0 END) as due_rev_c,
            COUNT(*) as total_c,
            COALESCE(MAX(mod), 0) as max_mod
        FROM cards WHERE queue != -1 GROUP BY did
    """, (today_days,))
    raw_stats = {}
    for r in cur.fetchall():
        raw_stats[r[0]] = {
            "new": r[1] or 0,
            "learning": r[2] or 0,
            "review": r[3] or 0,
            "total": r[4] or 0,
            "max_mod": r[5] or 0,
        }
    conn.close()
    result = []
    for did, raw_name in decks:
        child_ids = [
            d2[0] for d2 in decks
            if d2[1] == raw_name or d2[1].startswith(raw_name + "\x1f")
        ]
        tot_new = sum(raw_stats.get(cid, {}).get("new", 0) for cid in child_ids)
        tot_lrn = sum(raw_stats.get(cid, {}).get("learning", 0) for cid in child_ids)
        tot_rev = sum(raw_stats.get(cid, {}).get("review", 0) for cid in child_ids)
        tot_all = sum(raw_stats.get(cid, {}).get("total", 0) for cid in child_ids)
        max_mod = max((raw_stats.get(cid, {}).get("max_mod", 0) for cid in child_ids), default=0)
        fingerprint = f"{tot_all}_{max_mod}"
        norm_name = raw_name.replace("\x1f", "::")
        meta = DECK_META.get(norm_name, (norm_name, "Deck", "📁"))
        level = raw_name.count("\x1f")
        leaf_name = raw_name.split("\x1f")[-1]
        has_children = len(child_ids) > 1
        result.append({
            "id": did, "name": norm_name, "display_name": meta[0],
            "leaf_name": leaf_name, "category": meta[1], "icon": meta[2],
            "is_master": has_children, "has_children": has_children, "level": level,
            "new": tot_new, "learning": tot_lrn, "review": tot_rev, "total": tot_all,
            "fingerprint": fingerprint
        })
    return {"status": "ok", "today_days": today_days, "decks": result}


def get_deck_cards(did: int, limit: int = 0, full_sync: bool = False) -> Dict[str, Any]:
    conn = open_anki_db()
    cur = conn.cursor()
    today_days = get_today_days(cur)
    studied_kanji = get_user_studied_kanji()
    dids = get_deck_and_child_ids(cur, did)
    p_holders = ",".join("?" for _ in dids)
    if full_sync:
        cur.execute(f"""
            SELECT c.id, c.nid, c.did, c.queue, c.type, c.ivl, c.factor, c.reps, c.lapses, c.due,
                   n.mid, n.flds, d.name as deck_name
            FROM cards c
            JOIN notes n ON c.nid = n.id
            JOIN decks d ON c.did = d.id
            WHERE c.did IN ({p_holders}) AND c.queue != -1
            ORDER BY c.due ASC
        """, dids)
    else:
        order_clause = (
            "(c.queue = 2 AND c.due <= ?) DESC, "
            "(c.queue = 0) DESC, "
            "(c.queue = 1) DESC, "
            + ("RANDOM()" if len(dids) > 1 else "c.due ASC")
        )
        limit_clause = "LIMIT ?" if (limit and limit > 0) else ""
        query_params = (*dids, today_days, today_days) + ((limit,) if (limit and limit > 0) else ())
        cur.execute(f"""
            SELECT c.id, c.nid, c.did, c.queue, c.type, c.ivl, c.factor, c.reps, c.lapses, c.due,
                   n.mid, n.flds, d.name as deck_name
            FROM cards c
            JOIN notes n ON c.nid = n.id
            JOIN decks d ON c.did = d.id
            WHERE c.did IN ({p_holders})
              AND ((c.queue = 2 AND c.due <= ?) OR c.queue = 1 OR c.queue = 0)
            ORDER BY {order_clause}
            {limit_clause}
        """, query_params)
    rows = cur.fetchall()

    cur.execute(f"""
        SELECT SUM(CASE WHEN queue = 0 THEN 1 ELSE 0 END),
               SUM(CASE WHEN queue = 1 THEN 1 ELSE 0 END),
               SUM(CASE WHEN queue = 2 AND due <= ? THEN 1 ELSE 0 END),
               COUNT(*),
               COALESCE(MAX(mod), 0)
        FROM cards WHERE did IN ({p_holders}) AND queue != -1
    """, (today_days, *dids))
    c_row = cur.fetchone()
    counts = {"new": c_row[0] or 0, "learning": c_row[1] or 0, "review": c_row[2] or 0}
    fingerprint = f"{c_row[3] or 0}_{c_row[4] or 0}"

    cards = []
    dict_conn = open_dict_db()
    try:
        for r in rows:
            (
                cid, nid, c_did, queue, c_type, ivl, factor,
                reps, lapses, c_due, mid, flds_raw, dname
            ) = r
            flds = parse_anki_flds(flds_raw)
            c_data = format_card_data(mid, flds, dname, studied_kanji, dict_conn)
            cards.append({
                "id": cid, "nid": nid, "did": c_did, "deck_name": dname.replace("\x1f", "::"),
                "queue": queue, "type": c_type, "due": c_due, "ivl": ivl, "factor": factor,
                "reps": reps, "lapses": lapses,
                "due_time": (c_due * 1000) if queue == 1 else None,
                **c_data,
                "intervals": calculate_intervals_for_card(c_type, queue, ivl, factor)
            })
    finally:
        dict_conn.close()

    conn.close()
    return {"status": "ok", "counts": counts, "cards": cards, "fingerprint": fingerprint}

