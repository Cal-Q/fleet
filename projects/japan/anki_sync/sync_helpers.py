"""Helper routines for Anki synchronization and process management."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from pathlib import Path

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


def is_primary_anki_host() -> bool:
    """Check if current machine has standalone modern Anki 26 installed."""
    return os.path.isfile("/usr/local/share/anki/python/bin/python3")


def dispatch_remote_sync(cmd: str = "python3 /opt/japan/core/sync_and_push.py", timeout: int = 120) -> tuple[bool, str]:
    """Dispatch sync command to primary host (IONOS) where modern Anki runs."""
    try:
        ssh_cmd = ["ssh", "-o", "ConnectTimeout=8", "ionos", cmd]
        res = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
        output = (res.stdout + "\n" + res.stderr).strip()
        return res.returncode == 0, output
    except Exception as e:
        return False, str(e)

