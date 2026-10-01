#!/usr/bin/env python3
"""
api/routes/anki_log_routes.py — Anki Client Telemetry & Diagnostic Log Routes
Receives, stores, and serves rich client-side runtime logs for continuous observability.
Strictly <= 200 lines invariant.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/anki", tags=["anki_telemetry"])
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = "/opt/japan/logs" if os.path.exists("/opt/japan") else os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "anki_client_telemetry.jsonl")

_RECENT_LOGS: List[Dict[str, Any]] = []
MAX_IN_MEMORY = 1000


class LogBatchPayload(BaseModel):
    device: str = "unknown"
    timestamp: Optional[str] = None
    logs: List[Dict[str, Any]] = []


@router.post("/client_logs")
def ingest_client_logs(payload: LogBatchPayload) -> Dict[str, Any]:
    global _RECENT_LOGS
    received_count = len(payload.logs)
    if not received_count:
        return {"status": "ok", "received": 0}

    now_iso = datetime.utcnow().isoformat() + "Z"
    batch_meta = {
        "received_at": now_iso,
        "device": payload.device,
        "client_timestamp": payload.timestamp or now_iso
    }

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            for item in payload.logs:
                entry = {**batch_meta, **item}
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                _RECENT_LOGS.append(entry)

        if len(_RECENT_LOGS) > MAX_IN_MEMORY:
            _RECENT_LOGS = _RECENT_LOGS[-MAX_IN_MEMORY:]

        return {"status": "ok", "received": received_count, "total_buffered": len(_RECENT_LOGS)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Log ingestion failed: {str(e)}")


@router.get("/client_logs")
def get_client_logs(
    limit: int = Query(100, ge=1, le=500),
    level: Optional[str] = None,
    cat: Optional[str] = None,
    search: Optional[str] = None
) -> Dict[str, Any]:
    logs = list(_RECENT_LOGS)

    if not logs and os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()[-MAX_IN_MEMORY:]
                logs = [json.loads(line) for line in lines if line.strip()]
        except Exception:
            logs = []

    if level:
        lvl = level.upper()
        logs = [l for l in logs if l.get("level") == lvl]
    if cat:
        c = cat.upper()
        logs = [l for l in logs if l.get("cat") == c]
    if search:
        s = search.lower()
        logs = [
            l for l in logs
            if s in str(l.get("act", "")).lower() or s in str(l.get("det", "")).lower()
        ]

    return {
        "status": "ok",
        "count": len(logs[-limit:]),
        "total_available": len(logs),
        "logs": logs[-limit:]
    }


@router.delete("/client_logs")
def clear_client_logs() -> Dict[str, Any]:
    global _RECENT_LOGS
    _RECENT_LOGS = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write("")
        except Exception:
            pass
    return {"status": "ok", "cleared": True}


@router.post("/fatigue_event")
def record_fatigue_prompt_event(event: Dict[str, Any]) -> Dict[str, Any]:
    from core.anki_fatigue_snapshot_service import save_fatigue_prompt_event
    try:
        return save_fatigue_prompt_event(event)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record fatigue prompt: {str(e)}")


@router.get("/fatigue_events")
def list_fatigue_prompt_events(limit: int = Query(10, ge=1, le=50)) -> Dict[str, Any]:
    from core.anki_fatigue_snapshot_service import get_recent_fatigue_prompts
    try:
        events = get_recent_fatigue_prompts(limit=limit)
        return {"status": "ok", "count": len(events), "events": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch fatigue prompts: {str(e)}")


@router.get("/fatigue_events/latest")
def fetch_latest_fatigue_prompt() -> Dict[str, Any]:
    from core.anki_fatigue_snapshot_service import get_latest_fatigue_prompt
    try:
        event = get_latest_fatigue_prompt()
        return {"status": "ok", "event": event}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch latest fatigue prompt: {str(e)}")

