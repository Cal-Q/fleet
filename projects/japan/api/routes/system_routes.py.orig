#!/usr/bin/env python3
"""
tools/routes/system_routes.py — API routes for Application status, Universities, Dossiers, and Proxy
Strictly <= 200 lines invariant.
"""

import json
import os
import subprocess
import time
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter(tags=["system"])

WORKSPACE_DIR = "/opt/japan"
APPLICATIONS_DIR = os.path.join(WORKSPACE_DIR, "applications")
EXAMS_DIR = os.path.join(WORKSPACE_DIR, "exams")
RESEARCH_DIR = os.path.join(WORKSPACE_DIR, "research")
GDRIVE_ASSETS_DIR = "/mnt/gdrive_cold/assets/japan"
STATUS_FILE = os.path.join(APPLICATIONS_DIR, "application_status.json")
UNIS_FILE = os.path.join(APPLICATIONS_DIR, "universities_database.json")


class StatusUpdateRequest(BaseModel):
    item_id: str
    status: str
    notes: Optional[str] = None


@router.get("/api/status")
def get_status():
    if not os.path.exists(STATUS_FILE):
        from applications.checklist_tracker import load_state
        data = load_state()
    else:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

    total_bytes = 0
    for item in data.get("items", []):
        fpath = os.path.join(WORKSPACE_DIR, item.get("file_path", ""))
        drive_fpath = os.path.join(GDRIVE_ASSETS_DIR, item.get("file_path", ""))
        check_path = drive_fpath if os.path.exists(drive_fpath) else (fpath if os.path.exists(fpath) else None)
        if check_path:
            sz = os.path.getsize(check_path)
            item["exists"] = True
            item["size_bytes"] = sz
            item["size_str"] = f"{sz / 1024:.1f} KB"
            total_bytes += sz
        else:
            item["exists"] = False
            item["size_bytes"] = 0
            item["size_str"] = "Non trovato"

    data["total_attachment_bytes"] = total_bytes
    data["total_attachment_mb"] = f"{total_bytes / (1024 * 1024):.2f} MB"
    data["is_under_limit"] = total_bytes <= (10 * 1024 * 1024)
    return data


@router.post("/api/status/update")
def update_status(req: StatusUpdateRequest):
    if not os.path.exists(STATUS_FILE):
        raise HTTPException(status_code=404, detail="File di stato non trovato.")
    with open(STATUS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    found = False
    for item in data.get("items", []):
        if item["id"] == req.item_id:
            item["status"] = req.status
            if req.notes is not None:
                item["notes"] = req.notes
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="ID documento non trovato.")

    data["last_updated"] = datetime.now().isoformat()
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return {"success": True, "item_id": req.item_id, "status": req.status}


@router.get("/api/universities")
def get_universities(q: Optional[str] = None, type: Optional[str] = None, region: Optional[str] = None):
    if not os.path.exists(UNIS_FILE):
        raise HTTPException(status_code=404, detail="Database università non trovato.")
    with open(UNIS_FILE, "r", encoding="utf-8") as f:
        unis = json.load(f)

    if q:
        term = q.lower()
        unis = [u for u in unis if term in u["name_en"].lower() or term in u["name_ja"] or term in u["location_en"].lower()]
    if type:
        unis = [u for u in unis if type.lower() in u.get("course_types", [])]
    if region:
        unis = [u for u in unis if u.get("region") == region]
    return unis


@router.get("/api/proxy/ping")
def ping_embassy_proxy():
    t0 = time.time()
    cmd = [
        "sudo", "ssh", "-F", "/root/.ssh/config", "futro",
        'python3 -c "from curl_cffi import requests; r = requests.get(\\\'https://www.it.emb-japan.go.jp/itpr_it/studio_JapaneseStudies.html\\\', impersonate=\\\'chrome124\\\', timeout=15); print(r.status_code)"'
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
        elapsed = round((time.time() - t0), 2)
        code = res.stdout.decode().strip()
        if code == "200":
            return {"status": "online", "code": 200, "latency_sec": elapsed, "proxy_node": "Fujitsu Futro (residential TIM/Italy)"}
        return {"status": "error", "code": code, "latency_sec": elapsed, "stderr": res.stderr.decode()[:200]}
    except Exception as e:
        return {"status": "timeout_or_unreachable", "error": str(e)}


@router.api_route("/download/{category}/{filename}", methods=["GET", "HEAD"])
def download_document(category: str, filename: str):
    allowed_categories = {"applications": APPLICATIONS_DIR, "exams": EXAMS_DIR}
    if category not in allowed_categories:
        raise HTTPException(status_code=400, detail="Categoria non valida.")
    drive_path = os.path.join(GDRIVE_ASSETS_DIR, category, filename)
    if os.path.exists(drive_path):
        return FileResponse(drive_path, filename=filename, media_type="application/pdf")
    target_dir = allowed_categories[category]
    safe_path = os.path.abspath(os.path.join(target_dir, filename))
    if not safe_path.startswith(os.path.abspath(target_dir)) or not os.path.exists(safe_path):
        raise HTTPException(status_code=404, detail="File non trovato.")
    return FileResponse(safe_path, filename=filename, media_type="application/pdf")


@router.get("/api/research/dossiers")
def get_research_dossiers():
    if not os.path.exists(RESEARCH_DIR):
        return []
    dossiers = []
    for f in os.listdir(RESEARCH_DIR):
        if f.endswith(".md"):
            fpath = os.path.join(RESEARCH_DIR, f)
            stat = os.stat(fpath)
            title = f
            try:
                with open(fpath, "r", encoding="utf-8") as fp:
                    for line in fp:
                        if line.startswith("# "):
                            title = line.replace("# ", "").strip()
                            break
            except Exception:
                pass
            dossiers.append({
                "filename": f,
                "title": title,
                "size_bytes": stat.st_size,
                "size_str": f"{stat.st_size / 1024:.1f} KB",
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
    return sorted(dossiers, key=lambda x: x["modified"], reverse=True)


@router.get("/api/research/dossier/{filename}")
def get_research_dossier_content(filename: str):
    safe_path = os.path.abspath(os.path.join(RESEARCH_DIR, filename))
    if not safe_path.startswith(os.path.abspath(RESEARCH_DIR)) or not os.path.exists(safe_path):
        raise HTTPException(status_code=404, detail="Dossier non trovato.")
    with open(safe_path, "r", encoding="utf-8") as fp:
        content = fp.read()
    return {"filename": filename, "markdown": content}
