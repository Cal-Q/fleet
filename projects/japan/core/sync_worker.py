#!/usr/bin/env python3
"""
core/sync_worker.py — Single-Writer Synchronization Worker
Coordinates Anki collection mutations, deck generation, and AnkiWeb pushes.
Strictly <= 200 lines invariant.
"""

import os
import subprocess
import threading
import time
from typing import Optional, Tuple

REPO_ROOT = "/opt/japan/core"
SYNC_AND_PUSH_PATH = os.path.join(REPO_ROOT, "sync_and_push.py")
SYNC_QUICK_PATH = os.path.join(REPO_ROOT, "sync_quick.py")
ANKI_PYTHON = "/usr/local/share/anki/python/bin/python3"

_LOCK = threading.Lock()
_LAST_SYNC_TIME = 0.0
_LAST_SYNC_STATUS = "idle"
_DEBOUNCE_TIMER: Optional[threading.Timer] = None


def is_syncing() -> bool:
    return _LOCK.locked()


def get_sync_status() -> dict:
    return {
        "locked": _LOCK.locked(),
        "last_status": _LAST_SYNC_STATUS,
        "last_sync_timestamp": _LAST_SYNC_TIME
    }


def run_sync_and_push(timeout: int = 120) -> Tuple[bool, str]:
    global _LAST_SYNC_TIME, _LAST_SYNC_STATUS
    if not _LOCK.acquire(blocking=False):
        return False, "Sync worker is currently busy with another operation."

    try:
        _LAST_SYNC_STATUS = "running_sync_and_push"
        env = dict(os.environ)
        env["HOME"] = "/opt/japan"
        env["PYTHONPATH"] = "/usr/local/share/anki/app_packages"
        cmd = [ANKI_PYTHON, SYNC_AND_PUSH_PATH]
        res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout, env=env)
        _LAST_SYNC_TIME = time.time()
        output = (res.stdout + "\n" + res.stderr).strip()
        if res.returncode == 0:
            _LAST_SYNC_STATUS = "success"
            return True, output
        else:
            _LAST_SYNC_STATUS = f"error_code_{res.returncode}"
            return False, output
    except Exception as e:
        _LAST_SYNC_STATUS = f"exception_{str(e)}"
        return False, str(e)
    finally:
        _LOCK.release()


def run_sync_quick(timeout: int = 45) -> Tuple[bool, str]:
    global _LAST_SYNC_TIME, _LAST_SYNC_STATUS
    if not _LOCK.acquire(blocking=False):
        return False, "Sync worker is currently busy."

    try:
        _LAST_SYNC_STATUS = "running_sync_quick"
        env = dict(os.environ)
        env["HOME"] = "/opt/japan"
        env["PYTHONPATH"] = "/usr/local/share/anki/app_packages"
        cmd = [ANKI_PYTHON, SYNC_QUICK_PATH]
        res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout, env=env)
        _LAST_SYNC_TIME = time.time()
        output = (res.stdout + "\n" + res.stderr).strip()
        _LAST_SYNC_STATUS = "success" if res.returncode == 0 else f"error_{res.returncode}"
        return res.returncode == 0, output
    except Exception as e:
        _LAST_SYNC_STATUS = f"exception_{str(e)}"
        return False, str(e)
    finally:
        _LOCK.release()


def trigger_quick_sync_debounced(delay: float = 3.0) -> None:
    global _DEBOUNCE_TIMER
    if _DEBOUNCE_TIMER and _DEBOUNCE_TIMER.is_alive():
        _DEBOUNCE_TIMER.cancel()

    def _worker():
        run_sync_quick()

    _DEBOUNCE_TIMER = threading.Timer(delay, _worker)
    _DEBOUNCE_TIMER.daemon = True
    _DEBOUNCE_TIMER.start()
