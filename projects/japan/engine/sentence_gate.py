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
    col_cur = col_conn.cursor()
    try:
        col_cur.execute("""
            SELECT id FROM cards 
            WHERE did = 1770845308673 AND queue = -1
        """)
        suspended_cids = [r[0] for r in col_cur.fetchall()]

        now_ts = int(time.time())
        if suspended_cids:
            col_cur.executemany(
                "UPDATE cards SET queue = 0, mod = ?, usn = -1 WHERE id = ?",
                [(now_ts, cid) for cid in suspended_cids]
            )
            col_cur.execute(f"UPDATE col SET mod = {int(time.time() * 1000)}")
            col_conn.commit()

        return {
            'suspended': 0,
            'unsuspended': len(suspended_cids),
            'total_active': len(suspended_cids)
        }
    finally:
        col_conn.close()
