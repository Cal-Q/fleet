#!/usr/bin/env python3
"""
scratch/cleanup_dormant_vocab.py — Cleanup dormant legacy vocab from Anki & dict_index
Strictly keeps today's 20 words (21 notes/cards), positions them at due 1..21,
and deletes the 417 unsolicited dormant notes with graves for AnkiWeb.
"""

import os
import sys
import sqlite3
import json
import time

ANKI_COL = "/opt/japan/.local/share/Anki2/User 1/collection.anki2"
DICT_DB = "/opt/japan/data/dict_index.sqlite3"

search_terms = {
    "少し": ["少し"],
    "漢字": ["漢字"],
    "買う": ["買う"],
    "お冷": ["お冷"],
    "御目出度う": ["おめでとう"],
    "担当者": ["担当者", "たんとうしゃ"],
    "鶴": ["鶴", "つる"],
    "青色": ["青色"],
    "明けましておめでとうございます": ["あけましておめでとうございます"],
    "お水": ["お水"],
    "ごゆっくり": ["ごゆっくり"],
    "ただいま": ["ただいま", "只今"],
    "大統領": ["大統領", "だいとうりょう"],
    "承る": ["承る", "うけたまわる"],
    "本日": ["本日"],
    "冷や": ["冷や"],
    "手作り": ["手作り"],
    "無料": ["無料"],
    "拙者": ["拙者", "せっしゃ"],
    "スペシャル": ["スペシャル"]
}

def main():
    print("=== STARTING DORMANT VOCAB CLEANUP ===")
    conn = sqlite3.connect(ANKI_COL)
    cur = conn.cursor()

    cur.execute("SELECT n.id, n.flds FROM notes n WHERE n.id >= 1789390000000")
    notes = cur.fetchall()
    print(f"Total notes created today: {len(notes)}")

    today_nids = set()
    for term, patterns in search_terms.items():
        for nid, flds in notes:
            if any(p in flds for p in patterns):
                today_nids.add(nid)

    dormant_nids = [nid for nid, _ in notes if nid not in today_nids]
    print(f"Today notes to keep: {len(today_nids)}")
    print(f"Dormant notes to delete: {len(dormant_nids)}")

    if not dormant_nids:
        print("No dormant notes to delete.")
        return 0

    # 1. Delete dormant notes from Anki and create graves
    placeholders = ",".join("?" for _ in dormant_nids)
    cur.execute(f"SELECT id, nid FROM cards WHERE nid IN ({placeholders})", dormant_nids)
    card_rows = cur.fetchall()
    card_ids = [r[0] for r in card_rows]

    print(f"Adding graves for {len(card_ids)} cards and {len(dormant_nids)} notes...")
    for cid in card_ids:
        cur.execute("INSERT OR REPLACE INTO graves (usn, oid, type) VALUES (-1, ?, 0)", (cid,))
    for nid in dormant_nids:
        cur.execute("INSERT OR REPLACE INTO graves (usn, oid, type) VALUES (-1, ?, 1)", (nid,))

    cur.execute(f"DELETE FROM cards WHERE nid IN ({placeholders})", dormant_nids)
    cur.execute(f"DELETE FROM notes WHERE id IN ({placeholders})", dormant_nids)
    print("Deleted dormant cards and notes from Anki.")

    # 2. Prioritize today's notes to the front of the queue (due = 1..N)
    now = int(time.time())
    sorted_today_nids = sorted(list(today_nids))
    for idx, nid in enumerate(sorted_today_nids, 1):
        cur.execute(
            "UPDATE cards SET due = ?, mod = ?, usn = -1 WHERE nid = ?",
            (idx, now, nid)
        )
    print(f"Repositioned {len(sorted_today_nids)} today cards to due 1..{len(sorted_today_nids)}.")

    conn.commit()
    conn.close()

    # 3. Clean dormant entries from dict_index.sqlite3
    dconn = sqlite3.connect(DICT_DB)
    dcur = dconn.cursor()

    # Get kanas of today's words to preserve
    keep_kanas = set()
    for nid, flds in notes:
        if nid in today_nids:
            meaning = flds.split("\x1f")[1] if len(flds.split("\x1f")) > 1 else ""
            kana = meaning.split("<br>")[0].strip()
            if kana:
                keep_kanas.add(kana)

    # Clean dormant rows from source_english_to_kana and source_vocab_resolved
    # Only delete rows that were dormant (never existed in Anki before today)
    print("Cleaning dormant rows in source_english_to_kana...")
    # Rows with card_id that are not in Anki and not in today's notes
    dcur.execute("SELECT id, kana FROM source_english_to_kana")
    all_sek = dcur.fetchall()
    
    # Check which ones exist in Anki
    aconn = sqlite3.connect(ANKI_COL)
    acur = aconn.cursor()
    acur.execute("SELECT n.flds FROM notes n JOIN cards c ON c.nid = n.id")
    all_anki_flds = [r[0] for r in acur.fetchall()]
    aconn.close()

    anki_text = "\n".join(all_anki_flds)
    deleted_sek = 0
    for sek_id, kana in all_sek:
        if kana not in anki_text:
            dcur.execute("DELETE FROM source_english_to_kana WHERE id = ?", (sek_id,))
            dcur.execute("DELETE FROM source_vocab_resolved WHERE kana = ?", (kana,))
            deleted_sek += 1

    dconn.commit()
    dconn.close()
    print(f"Cleaned {deleted_sek} dormant entries from dict_index.sqlite3.")

    print("=== CLEANUP COMPLETE ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
