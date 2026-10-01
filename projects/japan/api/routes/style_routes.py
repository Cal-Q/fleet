#!/usr/bin/env python3
"""
tools/routes/style_routes.py — Style Lab and Japanese Aesthetic Matrix routes
Strictly <= 200 lines invariant.
"""

import json
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

router = APIRouter(tags=["styles"])

WORKSPACE_DIR = "/opt/japan"
STYLE_PREF_FILE = os.path.join(WORKSPACE_DIR, "japanese", "style_preference.json")

VALID_THEMES = {
    "muji": "無印良品 (MUJI Craft & Washi Texture)",
    "minimal": "Minimalist Japan",
    "zen": "Zen Garden",
    "wabi-sabi": "Wabi-Sabi",
    "sakura": "Cherry Blossom (Sakura)",
    "tokyo-night": "Tokyo Night",
    "cyberpunk": "Neo Tokyo Cyberpunk",
}


class StyleChoiceRequest(BaseModel):
    theme_id: str
    theme_name: str


@router.api_route("/styles", methods=["GET", "HEAD"])
def get_styles_page():
    return RedirectResponse(url="/", status_code=302)


@router.get("/api/styles/current")
def get_current_style():
    return {"theme_id": "muji", "theme_name": "無印良品 (MUJI Minimal)"}


@router.post("/api/styles/choose")
def choose_style(req: StyleChoiceRequest):
    if req.theme_id not in VALID_THEMES:
        raise HTTPException(status_code=400, detail="Tema non valido.")
    theme_name = VALID_THEMES[req.theme_id]
    data = {
        "theme_id": req.theme_id,
        "theme_name": theme_name
    }
    with open(STYLE_PREF_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return {"status": "ok", "saved": data}
