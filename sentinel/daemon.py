#!/usr/bin/env python3
"""
Fleet Sentinel Daemon: 24/7 background monitor for rule adherence across workspaces.
Strictly <= 200 lines and <= 100 characters per line.
"""
import os
import sys
import json
import time
import signal
from typing import Dict, Any

# Add sentinel module directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from constants import (
    VERSION,
    MONITORED_WORKSPACES,
    STATUS_JSON_PATH,
    VIOLATIONS_JSON_PATH,
    HEARTBEAT_JSON_PATH,
    DAEMON_INTERVAL_SECONDS,
    STATE_DIR
)
from code_guard import audit_directory
from constants_guard import audit_constants_directory
from connectivity_guard import audit_fleet_connectivity

running = True


def handle_stop(signum, frame):
    global running
    running = False


signal.signal(signal.SIGTERM, handle_stop)
signal.signal(signal.SIGINT, handle_stop)


def run_cycle() -> Dict[str, Any]:
    """Runs a single audit sweep across all monitored workspaces."""
    os.makedirs(STATE_DIR, exist_ok=True)
    t0 = time.time()

    code_violations = []
    constants_violations = []

    for ws in MONITORED_WORKSPACES:
        if os.path.isdir(ws):
            code_violations.extend(audit_directory(ws))
            constants_violations.extend(audit_constants_directory(ws))

    connectivity = audit_fleet_connectivity()
    elapsed = round(time.time() - t0, 3)

    total_violations = len(code_violations) + len(constants_violations)
    status_payload = {
        "version": VERSION,
        "timestamp": int(time.time()),
        "sweep_duration_sec": elapsed,
        "healthy": total_violations == 0,
        "total_code_violations": len(code_violations),
        "total_constants_violations": len(constants_violations),
        "connectivity": connectivity,
        "workspaces_monitored": [ws for ws in MONITORED_WORKSPACES if os.path.isdir(ws)]
    }

    # Write atomic status JSON
    tmp_status = STATUS_JSON_PATH + ".tmp"
    with open(tmp_status, "w", encoding="utf-8") as f:
        json.dump(status_payload, f, indent=2)
    os.replace(tmp_status, STATUS_JSON_PATH)

    # Write detailed violations JSON
    violations_payload = {
        "timestamp": int(time.time()),
        "code_violations": code_violations,
        "constants_violations": constants_violations
    }
    tmp_viol = VIOLATIONS_JSON_PATH + ".tmp"
    with open(tmp_viol, "w", encoding="utf-8") as f:
        json.dump(violations_payload, f, indent=2)
    os.replace(tmp_viol, VIOLATIONS_JSON_PATH)

    return status_payload


def main():
    while running:
        try:
            run_cycle()
        except Exception as err:
            sys.stderr.write(f"Sentinel sweep error: {err}\n")

        slept = 0
        while running and slept < DAEMON_INTERVAL_SECONDS:
            time.sleep(1)
            slept += 1


if __name__ == "__main__":
    main()
