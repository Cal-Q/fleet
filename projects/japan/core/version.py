"""
core/version.py — Single Source of Truth for App Version & Build Metadata
Strictly <= 200 lines and <= 100 cols invariant.
"""
import json
from pathlib import Path
from typing import Dict, Any

VERSION_FILE = Path(__file__).resolve().parent.parent / "version.json"


def get_version_info() -> Dict[str, Any]:
    if VERSION_FILE.exists():
        try:
            return json.loads(VERSION_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"version": "v2.10.16", "build": "20260930_v2116"}


APP_VERSION = get_version_info().get("version", "v2.10.16")
APP_BUILD = get_version_info().get("build", "20260930_v2116")
