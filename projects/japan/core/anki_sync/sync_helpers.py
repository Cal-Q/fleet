"""Helper routines for Anki synchronization and process management."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

ANKICONNECT_URL = "http://localhost:8765"
ANKICONNECT_POLL_TIMEOUT_SECONDS = 60
ANKICONNECT_POLL_INTERVAL_SECONDS = 0.1
ANKI_DEFAULT_BASE = "/opt/japan/.local/share/Anki2"
ANKI_DEFAULT_PROFILE = "User 1"


def get_anki_base_and_profile(repo_root: Path) -> tuple[str, str]:
    config_file = repo_root / "config.json"
    if config_file.is_file():
        try:
            with open(config_file, "r", encoding="utf-8-sig") as f:
                cfg = json.load(f)
            col_path = Path(cfg["AnkiCollectionPath"])
            return str(col_path.parent.parent), col_path.parent.name
        except Exception:
            pass
    return ANKI_DEFAULT_BASE, ANKI_DEFAULT_PROFILE


def anki_already_running() -> bool:
    result = subprocess.run(["pgrep", "-x", "anki"], capture_output=True, text=True)
    return result.returncode == 0


def _signal_group(pid: int, sig: signal.Signals) -> None:
    try:
        os.killpg(os.getpgid(pid), sig)
    except ProcessLookupError:
        pass


def close_anki_process(anki_process: subprocess.Popen) -> None:
    _signal_group(anki_process.pid, signal.SIGTERM)
    try:
        anki_process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        _signal_group(anki_process.pid, signal.SIGKILL)
        try:
            anki_process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass


def ankiconnect_request(action: str, timeout: float = 10) -> dict | None:
    payload = json.dumps({"action": action, "version": 6}).encode("utf-8")
    request = urllib.request.Request(ANKICONNECT_URL, data=payload)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())
    except Exception:
        return None


def wait_for_ankiconnect() -> bool:
    deadline = time.monotonic() + ANKICONNECT_POLL_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if ankiconnect_request("version") is not None:
            return True
        time.sleep(ANKICONNECT_POLL_INTERVAL_SECONDS)
    return False


def sync_via_anki_gui(base_dir: str, profile_name: str) -> bool:
    anki_process = subprocess.Popen(
        ["xvfb-run", "-a", "anki", "-b", base_dir, "-p", profile_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        if not wait_for_ankiconnect():
            return False
        sync_result = ankiconnect_request("sync", timeout=120)
        if sync_result is None or sync_result.get("error"):
            return False
        ankiconnect_request("guiExitAnki")
        return True
    finally:
        close_anki_process(anki_process)
