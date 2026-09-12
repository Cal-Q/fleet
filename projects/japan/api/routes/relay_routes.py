#!/usr/bin/env python3
"""
api/routes/relay_routes.py — Tampermonkey Userscript & Clipboard Relay Bridge
Replaces legacy Express server.js. Serves userscript and handles AnkiConnect-style requests.
Strictly <= 200 lines invariant.
"""

import json
import os
import re
import urllib.parse
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Request, Response
from fastapi.responses import FileResponse, JSONResponse

from core.sync_worker import trigger_quick_sync_debounced

router = APIRouter(tags=["relay"])

BASE_DIR = "/opt/japan"
DATA_DIR = os.path.join(BASE_DIR, "data")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
USERSCRIPT_PATH = os.path.join(PUBLIC_DIR, "bunpro-anki.user.js")
DB_FILE = os.path.join(DATA_DIR, "bunpro_db.json")
PENDING_VOCAB_FILE = os.path.join(DATA_DIR, "bunpro_vocab_pending.json")
KNOWN_VOCAB_FILE = os.path.join(DATA_DIR, "bunpro_vocab_known.json")
PENDING_SENTENCES_FILE = os.path.join(DATA_DIR, "bunpro_sentences_pending.json")
ANKI_INFO_FILE = os.path.join(DATA_DIR, "anki_info.json")

_FRONT_TO_ID: Dict[str, int] = {}
_ID_TO_FRONT: Dict[int, str] = {}
_NEXT_ID = 1


def _get_id_for_front(front: str) -> int:
    global _NEXT_ID
    if front not in _FRONT_TO_ID:
        _FRONT_TO_ID[front] = _NEXT_ID
        _ID_TO_FRONT[_NEXT_ID] = front
        _NEXT_ID += 1
    return _FRONT_TO_ID[front]


def _read_json_safe(file_path: str, default: Any) -> Any:
    if not os.path.exists(file_path):
        return default
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json_atomic(file_path: str, data: Any) -> None:
    tmp = file_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, file_path)


@router.get("/scripts/bunpro-anki.user.js")
def get_userscript():
    if not os.path.exists(USERSCRIPT_PATH):
        return Response("// Userscript not found", status_code=404, media_type="text/javascript")
    return FileResponse(USERSCRIPT_PATH, media_type="text/javascript")


@router.get("/api/copied-items")
def get_copied_items():
    return _read_json_safe(DB_FILE, [])


@router.post("/api/copied-items")
async def post_copied_item(request: Request):
    body = await request.json()
    url = body.get("url")
    if not url:
        return JSONResponse({"error": "URL is required"}, status_code=400)
    try:
        norm = urllib.parse.unquote(url)
    except Exception:
        norm = url
    items = _read_json_safe(DB_FILE, [])
    if norm not in items:
        items.append(norm)
        _write_json_atomic(DB_FILE, items)
    return JSONResponse({"success": True, "url": norm}, status_code=201)


@router.delete("/api/copied-items")
async def delete_copied_item(request: Request):
    body = await request.json()
    url = body.get("url")
    if not url:
        return JSONResponse({"error": "URL is required"}, status_code=400)
    try:
        norm = urllib.parse.unquote(url)
    except Exception:
        norm = url
    items = _read_json_safe(DB_FILE, [])
    new_items = [i for i in items if i != norm]
    _write_json_atomic(DB_FILE, new_items)
    return {"success": True}


@router.post("/api/anki-info")
async def post_anki_info(request: Request):
    body = await request.json()
    _write_json_atomic(ANKI_INFO_FILE, body)
    return {"success": True}


@router.post("/api/vocab-relay")
async def vocab_relay(request: Request):
    body = await request.json()
    action = body.get("action")
    params = body.get("params", {}) or {}

    pending = _read_json_safe(PENDING_VOCAB_FILE, {})
    known = _read_json_safe(KNOWN_VOCAB_FILE, {})

    if action == "findNotes":
        query = params.get("query", "")
        match = re.search(r'"Front:(.*)"$', query)
        front = match.group(1) if match else None
        exists = front and (front in pending or front in known)
        return {"result": [_get_id_for_front(front)] if exists else [], "error": None}

    elif action == "notesInfo":
        notes = params.get("notes", [])
        results = []
        for nid in notes:
            front = _ID_TO_FRONT.get(nid)
            if not front:
                continue
            back = pending.get(front) or known.get(front)
            if back is not None:
                results.append({"noteId": nid, "fields": {"Front": {"value": front}, "Back": {"value": back}}})
        return {"result": results, "error": None}

    elif action == "addNotes":
        notes = params.get("notes", [])
        results = []
        VOCAB_DECK = "[SOURCE] English -> Kana"
        for n in notes:
            if n.get("deckName") != VOCAB_DECK:
                results.append(None)
                continue
            fields = n.get("fields", {})
            front = fields.get("Front", "")
            back = fields.get("Back", "")
            if front in pending or front in known:
                results.append(None)
                continue
            pending[front] = back
            results.append(_get_id_for_front(front))
        _write_json_atomic(PENDING_VOCAB_FILE, pending)
        trigger_quick_sync_debounced()
        return {"result": results, "error": None}

    elif action == "updateNoteFields":
        note = params.get("note", {})
        nid = note.get("id")
        front = _ID_TO_FRONT.get(nid)
        fields = note.get("fields", {})
        if front and "Back" in fields:
            pending[front] = fields["Back"]
            _write_json_atomic(PENDING_VOCAB_FILE, pending)
            trigger_quick_sync_debounced()
        return {"result": None, "error": None}

    return {"result": None, "error": f"unsupported action: {action}"}


@router.post("/api/sentence-relay")
async def sentence_relay(request: Request):
    body = await request.json()
    action = body.get("action")
    params = body.get("params", {}) or {}

    if action == "addNotes":
        existing = _read_json_safe(PENDING_SENTENCES_FILE, [])
        notes = params.get("notes", [])
        results = []
        import time
        for n in notes:
            existing.append(n)
            results.append(int(time.time() * 1000))
        _write_json_atomic(PENDING_SENTENCES_FILE, existing)
        trigger_quick_sync_debounced()
        return {"result": results, "error": None}

    return {"result": None, "error": f"unsupported action: {action}"}
