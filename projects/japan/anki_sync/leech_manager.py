"""Leech and Suspended Card Lifecycle Management."""

from __future__ import annotations

import logging
import time
from typing import NamedTuple

from anki.collection import Collection

log = logging.getLogger("leech_manager")


class LeechCycleResult(NamedTuple):
    dconf_updated: int
    newly_suspended: list[int]
    rehabilitated: list[dict]


def enforce_leech_suspend_config(col: Collection) -> int:
    """Ensures all deck configurations have leechAction = 0 (Suspend on leech)."""
    updated = 0
    for conf in col.decks.all_config():
        lapse = conf.get("lapse", {})
        if lapse.get("leechAction") != 0:
            lapse["leechAction"] = 0
            conf["lapse"] = lapse
            col.decks.save(conf)
            updated += 1
    return updated


def suspend_active_leeches(col: Collection) -> list[int]:
    """Finds all cards that are leeches (tagged 'leech' or lapses >= 8) but currently active, and suspends them."""
    rows = col.db.all("""
        SELECT c.id
        FROM cards c
        JOIN notes n ON c.nid = n.id
        WHERE c.queue != -1
          AND (n.tags LIKE "% leech %" OR n.tags LIKE "leech %" OR n.tags LIKE "% leech" OR n.tags = "leech" OR c.lapses >= 8)
    """)
    cids_to_suspend = [r[0] for r in rows]
    if cids_to_suspend:
        col.sched.suspend_cards(cids_to_suspend)
    return cids_to_suspend


def rehabilitate_suspended_cards(col: Collection, cooldown_days: int = 30) -> list[dict]:
    """Inspects all suspended cards and rehabilitates those whose cooldown has expired."""
    now_ms = int(time.time() * 1000)
    cooldown_ms = cooldown_days * 86400 * 1000

    rows = col.db.all("""
        SELECT c.id, c.nid, c.did, max(r.id) as last_rev
        FROM cards c
        LEFT JOIN revlog r ON r.cid = c.id
        WHERE c.queue = -1 AND c.did != 1770845308673
        GROUP BY c.id
    """)

    eligible_cids: list[int] = []
    eligible_info: list[dict] = []

    for cid, nid, did, last_rev in rows:
        ref_ms = last_rev if last_rev else cid
        if (now_ms - ref_ms) >= cooldown_ms:
            eligible_cids.append(cid)
            deck = col.decks.get(did)
            deck_name = deck.get("name", str(did)) if deck else str(did)
            days_elapsed = (now_ms - ref_ms) / (86400 * 1000)
            eligible_info.append({
                "cid": cid,
                "nid": nid,
                "deck": deck_name,
                "days_elapsed": round(days_elapsed, 1),
                "had_reviews": bool(last_rev),
            })

    if not eligible_cids:
        return []

    col.sched.unsuspend_cards(eligible_cids)
    col.sched.reset_cards(eligible_cids)

    nids_to_clean = {item["nid"] for item in eligible_info}
    for nid in nids_to_clean:
        try:
            note = col.get_note(nid)
            if note.has_tag("leech"):
                note.remove_tag("leech")
                col.update_note(note)
        except Exception:
            pass

    return eligible_info


def process_leech_lifecycle(col: Collection, cooldown_days: int = 30) -> LeechCycleResult:
    dconf_updated = enforce_leech_suspend_config(col)
    newly_suspended = suspend_active_leeches(col)
    rehabilitated = rehabilitate_suspended_cards(col, cooldown_days=cooldown_days)
    return LeechCycleResult(dconf_updated, newly_suspended, rehabilitated)
