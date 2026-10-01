#!/usr/bin/env python3
"""
engine/vocab_meanings_resolver.py — JMdict Multi-Meaning Resolution
Extracts and prioritizes English glosses for Japanese vocabulary terms.
Strictly <= 200 lines invariant.
"""

from collections import defaultdict
from typing import Dict, List


def resolve_multi_meanings(
    cur, word: str, reading: str, input_meaning: str = "", limit: int = 3
) -> List[str]:
    cur.execute(
        """
        SELECT re.entry_id, (re.reading = ?) as is_exact_word
        FROM reading_elements re
        JOIN entries e ON re.entry_id = e.id
        WHERE re.reading IN (?, ?) AND e.is_name_entry = 0
        ORDER BY is_exact_word DESC, re.ord ASC
        """,
        (word, word, reading),
    )
    rows = cur.fetchall()
    if not rows:
        return [input_meaning] if input_meaning else []

    entry_id = rows[0][0]
    cur.execute(
        """
        SELECT s.id, g.text FROM senses s
        JOIN glosses g ON g.sense_id = s.id
        WHERE s.entry_id = ? AND g.language = 'eng'
        ORDER BY s.ord ASC, g.ord ASC
        """,
        (entry_id,),
    )
    sense_rows = cur.fetchall()

    senses_dict: Dict[int, List[str]] = defaultdict(list)
    for s_id, text in sense_rows:
        t = (text or "").strip()
        if t:
            senses_dict[s_id].append(t)

    input_lower = input_meaning.lower().strip()
    result = []
    seen = set()

    for s_id, gloss_list in senses_dict.items():
        for g in gloss_list:
            g_low = g.lower()
            matches = input_lower and (
                input_lower == g_low or input_lower in g_low or g_low in input_lower
            )
            if matches:
                if g_low not in seen:
                    result.append(g)
                    seen.add(g_low)
                break
        if result:
            break

    for s_id, gloss_list in senses_dict.items():
        if len(result) >= limit:
            break
        g0 = gloss_list[0]
        if g0.lower() not in seen:
            result.append(g0)
            seen.add(g0.lower())

    for s_id, gloss_list in senses_dict.items():
        if len(result) >= limit:
            break
        for g in gloss_list[1:]:
            if len(result) >= limit:
                break
            if g.lower() not in seen:
                result.append(g)
                seen.add(g.lower())

    return result if result else ([input_meaning] if input_meaning else [])
