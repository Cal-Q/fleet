#!/usr/bin/env python3
"""
api/routes/srs_routes.py — SRS Review Telemetry & Anki Profile API Routes
Provides profile stats, zero-due verification, and leech management.
Strictly <= 200 lines invariant.
"""

import os
from fastapi import APIRouter, HTTPException

from core.db import open_anki_db
from core.sync_worker import run_sync_and_push
from engine.srs_telemetry import get_bunki_profile, verify_travel_srs

router = APIRouter(tags=["srs"])


@router.get("/api/bunki/profile")
def api_get_bunki_profile():
    try:
        return get_bunki_profile()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/bunki/sync")
def api_trigger_bunki_sync():
    try:
        ok, msg = run_sync_and_push()
        if not ok:
            raise HTTPException(status_code=500, detail=f"Sync failed: {msg}")
        return get_bunki_profile()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/bunki/srs_status")
def api_get_srs_status():
    try:
        return verify_travel_srs(do_sync=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/bunki/verify_srs")
def api_verify_srs():
    try:
        return verify_travel_srs(do_sync=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/leeches")
def api_get_leeches():
    try:
        conn = open_anki_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT cards.id, notes.flds, cards.lapses 
            FROM cards 
            JOIN notes ON cards.nid = notes.id 
            WHERE cards.queue = -1 
            ORDER BY cards.lapses DESC 
            LIMIT 50
        """)
        items = []
        for cid, flds, lapses in cur.fetchall():
            parts = flds.split(chr(31))
            word = parts[0] if parts else ""
            items.append({"card_id": cid, "front": word, "lapses": lapses})
        conn.close()
        return {"status": "ok", "items": items}
    except Exception as e:
        return {"status": "error", "items": [], "detail": str(e)}


@router.post("/api/leeches/review")
def api_post_leech_review(req: dict):
    cid = req.get("card_id")
    action = req.get("action", "rehabilitate")
    if not cid:
        raise HTTPException(status_code=400, detail="card_id missing")
    try:
        conn = open_anki_db()
        cur = conn.cursor()
        if action == "rehabilitate":
            cur.execute("""
                UPDATE cards 
                SET queue = 2, type = 2, ivl = 1, factor = 1500, lapses = 0, usn = -1 
                WHERE id = ?
            """, (cid,))
            cur.execute("SELECT nid FROM cards WHERE id = ?", (cid,))
            row = cur.fetchone()
            if row:
                nid = row[0]
                cur.execute("SELECT tags FROM notes WHERE id = ?", (nid,))
                trow = cur.fetchone()
                if trow and trow[0]:
                    cleaned_tags = " ".join([t for t in trow[0].split() if t != "leech"])
                    cur.execute("UPDATE notes SET tags = ?, usn = -1 WHERE id = ?", (cleaned_tags, nid))
        elif action == "retire":
            cur.execute("SELECT nid FROM cards WHERE id = ?", (cid,))
            row = cur.fetchone()
            if row:
                nid = row[0]
                cur.execute("SELECT tags FROM notes WHERE id = ?", (nid,))
                trow = cur.fetchone()
                existing = trow[0] if trow and trow[0] else ""
                if "retired_leech" not in existing:
                    new_tags = f"{existing} retired_leech".strip()
                    cur.execute("UPDATE notes SET tags = ?, usn = -1 WHERE id = ?", (new_tags, nid))
        conn.commit()
        conn.close()
        return {"status": "ok", "action": action, "card_id": cid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

