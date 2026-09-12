#!/usr/bin/env python3
"""
engine/sentence_gate.py — Vocab-First Sentence Gating & Suspension
Suspends 0-review sentence cards if required vocabulary is unreviewed.
Strictly <= 200 lines invariant.
"""

import json
import re
import time
from typing import Any, Dict
from bs4 import BeautifulSoup

from core.db import open_anki_db, open_dict_db


def audit_and_suspend_sentences() -> Dict[str, Any]:
    col_conn = open_anki_db(timeout=15.0)
    dict_conn = open_dict_db()
    
    col_cur = col_conn.cursor()
    dict_cur = dict_conn.cursor()

    from engine.grammar_vocab_gate import get_reviewed_vocab_set
    rev_set = get_reviewed_vocab_set()

    try:
        # 1. Get 0-review cards in Jap Sentences (did 1770845308673)
        col_cur.execute("""
            SELECT cards.id, cards.queue, notes.flds 
            FROM cards 
            JOIN notes ON cards.nid = notes.id 
            WHERE cards.did = 1770845308673 AND cards.reps = 0
        """)
        cards_0 = col_cur.fetchall()

        to_suspend = []
        to_unsuspend = []

        for cid, queue, flds in cards_0:
            parts = flds.split(chr(31))
            en = parts[0].strip() if len(parts) > 0 else ""
            jp_raw = parts[1].strip() if len(parts) > 1 else ""
            
            soup = BeautifulSoup(jp_raw, 'html.parser')
            for rt in soup.find_all(['rt', 'rp']):
                rt.decompose()
            plain = re.sub(r'\s+', '', soup.get_text('', strip=True))

            dict_cur.execute(
                'SELECT grammar_id FROM bunpro_grammar_sentences WHERE plain_jp = ? OR clean_en = ? LIMIT 1',
                (plain, en)
            )
            row = dict_cur.fetchone()
            if row:
                gid = row[0]
                dict_cur.execute('SELECT title FROM bunpro_grammar_vocab_coverage WHERE grammar_id = ?', (gid,))
                titles = [r[0] for r in dict_cur.fetchall()]
                active_words = [t for t in titles if t in plain or t in jp_raw]
                unreviewed = [w for w in active_words if w not in rev_set]

                if unreviewed and queue != -1:
                    to_suspend.append(cid)
                elif not unreviewed and queue == -1:
                    to_unsuspend.append(cid)
            else:
                if queue != -1:
                    to_suspend.append(cid)

        # Apply suspensions directly to cards table
        now_ts = int(time.time())
        if to_suspend:
            col_cur.executemany(
                "UPDATE cards SET queue = -1, mod = ?, usn = -1 WHERE id = ?",
                [(now_ts, cid) for cid in to_suspend]
            )
        if to_unsuspend:
            col_cur.executemany(
                "UPDATE cards SET queue = 0, mod = ?, usn = -1 WHERE id = ?",
                [(now_ts, cid) for cid in to_unsuspend]
            )

        if to_suspend or to_unsuspend:
            col_cur.execute(f"UPDATE col SET mod = {int(time.time() * 1000)}")
            col_conn.commit()

        return {
            'suspended': len(to_suspend),
            'unsuspended': len(to_unsuspend),
            'total_zero_rep': len(cards_0)
        }
    finally:
        col_conn.close()
        dict_conn.close()
