#!/usr/bin/env python3
"""
scripts/deduplicate_and_restore_kanji_vocab.py — Deduplicates and Restores Kanji Vocab
Merges shadow pure-kana duplicates into authentic Kanji cards and promotes fallbacks.
Strictly <= 200 lines invariant.
"""

import os
import re
import shutil
import sqlite3
import time
from typing import Any, Dict, List, Set, Tuple

BASE_DIR = "/opt/japan"
ANKI_DB = os.path.join(BASE_DIR, ".local/share/Anki2/User 1/collection.anki2")
if not os.path.exists(ANKI_DB):
    ANKI_DB = os.path.expanduser("~/.local/share/Anki2/User 1/collection.anki2")


def sanitize_meanings(meaning_text: str) -> Tuple[str, List[str]]:
    lines = [l.strip() for l in meaning_text.split("<br>") if l.strip()]
    if not lines:
        return "", []
    reading = lines[0]
    meanings = []
    seen = set()
    for l in lines[1:]:
        clean = re.sub(r"\s*\[[\u4e00-\u9faf]+.*?\]", "", l).strip()
        if clean.startswith("- "):
            clean = clean[2:].strip()
        if clean and clean.lower() not in seen:
            meanings.append(clean)
            seen.add(clean.lower())
    return reading, meanings


def run_deduplication_and_restoration(dry_run: bool = False) -> Dict[str, Any]:
    print(f"[*] Starting Vocabulary Deduplication & Kanji Restoration (dry_run={dry_run})...")
    conn = sqlite3.connect(ANKI_DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT n.id, n.flds, c.id, c.queue, c.due, c.ivl, c.reps, c.lapses, c.factor
        FROM notes n
        JOIN cards c ON c.nid = n.id
        WHERE c.did = 1759999324396
    """)
    rows = cur.fetchall()

    kanji_notes: Dict[str, Dict[str, Any]] = {}
    kana_notes: Dict[str, List[Dict[str, Any]]] = {}

    for nid, flds, cid, queue, due, ivl, reps, lapses, factor in rows:
        parts = flds.split("\x1f")
        front = parts[0] if len(parts) > 0 else ""
        meaning = parts[1] if len(parts) > 1 else ""
        clean_front = re.sub(r"<.*?>", "", front).strip()

        info = {
            "nid": nid, "cid": cid, "front": front, "clean_front": clean_front,
            "meaning": meaning, "queue": queue, "due": due, "ivl": ivl,
            "reps": reps, "lapses": lapses, "factor": factor
        }

        if any("\u4e00" <= c <= "\u9faf" for c in clean_front):
            kanji_notes[clean_front] = info
        else:
            kana_notes.setdefault(clean_front, []).append(info)

    merges: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    promotions: List[Tuple[Dict[str, Any], str]] = []

    for kana_front, k_list in kana_notes.items():
        for kana_note in k_list:
            meaning = kana_note["meaning"]
            bracket_kanji = re.findall(r"\[([\u4e00-\u9faf]+.*?)\]", meaning)
            target_k = bracket_kanji[0].strip() if bracket_kanji else None

            if target_k and target_k in kanji_notes:
                merges.append((kanji_notes[target_k], kana_note))
            elif target_k:
                promotions.append((kana_note, target_k))
            else:
                matched_kanji = None
                for k_lemma, k_note in kanji_notes.items():
                    k_reading = k_note["meaning"].split("<br>")[0].strip()
                    clean_k_rd = re.sub(r"[（\(].*?[）\)]", "", k_reading).strip()
                    if clean_k_rd == kana_front and k_lemma != kana_front and kana_note["reps"] == 0:
                        matched_kanji = k_note
                        break
                if matched_kanji:
                    merges.append((matched_kanji, kana_note))

    print(f"[+] Found {len(merges)} duplicate merges and {len(promotions)} promotions.")

    if dry_run:
        conn.close()
        return {"merges": len(merges), "promotions": len(promotions)}

    # Create Backup
    backup_path = ANKI_DB + f".bak_dedup_{int(time.time())}"
    shutil.copy2(ANKI_DB, backup_path)
    print(f"[+] Backup saved: {backup_path}")

    now_ms = int(time.time() * 1000)

    # 1. Execute Merges
    deleted_nids = set()
    for kanji_note, kana_note in merges:
        k_nid = kanji_note["nid"]
        kana_nid = kana_note["nid"]

        k_rd, k_meanings = sanitize_meanings(kanji_note["meaning"])
        kana_rd, kana_meanings = sanitize_meanings(kana_note["meaning"])

        # Combined unique meanings, preserving order
        combined_meanings = list(k_meanings)
        seen = {m.lower() for m in combined_meanings}
        for m in kana_meanings:
            if m.lower() not in seen:
                combined_meanings.append(m)
                seen.add(m.lower())

        reading_final = k_rd or kana_rd
        new_meaning_fld = f"{reading_final}<br>" + "<br>".join(f"- {m}" for m in combined_meanings)
        new_flds = f"{kanji_note['front']}\x1f{new_meaning_fld}\x1f"

        # Inherit review progress if kana note was more mature
        best_reps = max(kanji_note["reps"], kana_note["reps"])
        best_ivl = max(kanji_note["ivl"], kana_note["ivl"])
        best_queue = kanji_note["queue"] if kanji_note["reps"] >= kana_note["reps"] else kana_note["queue"]
        best_due = kanji_note["due"] if kanji_note["reps"] >= kana_note["reps"] else kana_note["due"]

        cur.execute("UPDATE notes SET flds = ?, mod = ?, usn = -1 WHERE id = ?", (new_flds, int(time.time()), k_nid))
        cur.execute(
            "UPDATE cards SET reps = ?, ivl = ?, queue = ?, due = ?, mod = ?, usn = -1 WHERE nid = ?",
            (best_reps, best_ivl, best_queue, best_due, int(time.time()), k_nid)
        )

        cur.execute("DELETE FROM cards WHERE nid = ?", (kana_nid,))
        cur.execute("DELETE FROM notes WHERE id = ?", (kana_nid,))
        deleted_nids.add(kana_nid)

    # 2. Execute Promotions
    promoted_count = 0
    for kana_note, target_k in promotions:
        nid = kana_note["nid"]
        rd, meanings = sanitize_meanings(kana_note["meaning"])
        new_meaning_fld = f"{rd}<br>" + "<br>".join(f"- {m}" for m in meanings)
        new_flds = f"{target_k}\x1f{new_meaning_fld}\x1f"
        cur.execute("UPDATE notes SET flds = ?, mod = ?, usn = -1 WHERE id = ?", (new_flds, int(time.time()), nid))
        promoted_count += 1

    cur.execute("UPDATE col SET mod = ?, usn = -1", (now_ms,))
    conn.commit()
    conn.close()

    print(f"[+] SUCCESS: Merged {len(merges)} duplicate cards, deleted {len(deleted_nids)} shadow notes, promoted {promoted_count} cards to authentic Kanji.")
    return {"merged": len(merges), "deleted": len(deleted_nids), "promoted": promoted_count}


if __name__ == "__main__":
    run_deduplication_and_restoration(dry_run=False)
