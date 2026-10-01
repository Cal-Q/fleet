#!/usr/bin/env python3
"""
Fleet Audit CLI: On-demand terminal inspector for fleet rules and sentinel status.
Strictly <= 200 lines and <= 100 characters per line.
"""
import os
import sys
import json

# Add sentinel module directory to path
sys.path.insert(0, "/opt/fleet/sentinel")

from constants import (
    STATUS_JSON_PATH,
    VIOLATIONS_JSON_PATH
)
from daemon import run_cycle


def print_report(status: dict, violations: dict):
    print("=" * 60)
    print(" FLEET SENTINEL & RULES AUDIT REPORT")
    print(f" Version: {status.get('version', '1.0.0')} | Status: "
          f"{'✅ COMPLIANT' if status.get('healthy') else '⚠️ VIOLATIONS DETECTED'}")
    print("=" * 60)

    print("\n📡 Remote Node Connectivity:")
    for node in status.get("connectivity", []):
        name = node.get("name", "unknown")
        alive = node.get("alive", False)
        lat = node.get("latency_ms")
        icon = "🟢" if alive else "🔴"
        lat_str = f"({lat} ms)" if lat is not None else ""
        err_str = f" - Error: {node.get('error')}" if not alive else ""
        print(f"  {icon} {name.upper()}: {'CONNECTED' if alive else 'DISCONNECTED'} {lat_str}{err_str}")

    print("\n📁 Code Quality (Rule 3: Lines <= 200, Chars <= 100):")
    code_viols = violations.get("code_violations", [])
    if not code_viols:
        print("  ✅ All monitored workspace files comply with modular limits.")
    else:
        print(f"  ⚠️ {len(code_viols)} files with modularity violations:")
        for entry in code_viols[:5]:
            print(f"    - {entry.get('file')}: {len(entry.get('violations', []))} violations")
        if len(code_viols) > 5:
            print(f"    ... and {len(code_viols) - 5} more files.")

    print("\n🔒 Constants & Hardcoded Literals (Rule 5):")
    const_viols = violations.get("constants_violations", [])
    if not const_viols:
        print("  ✅ No hardcoded URLs/IPs in logic files. Using constants registries.")
    else:
        print(f"  ⚠️ {len(const_viols)} files with hardcoded literals:")
        for entry in const_viols[:5]:
            print(f"    - {entry.get('file')}: {len(entry.get('violations', []))} literals")
        if len(const_viols) > 5:
            print(f"    ... and {len(const_viols) - 5} more files.")

    print("=" * 60)


def main():
    if "--live" in sys.argv or not os.path.exists(STATUS_JSON_PATH):
        print("Running live audit sweep across all workspaces...")
        status = run_cycle()
        with open(VIOLATIONS_JSON_PATH, "r") as f:
            violations = json.load(f)
    else:
        with open(STATUS_JSON_PATH, "r") as f:
            status = json.load(f)
        with open(VIOLATIONS_JSON_PATH, "r") as f:
            violations = json.load(f)

    print_report(status, violations)


if __name__ == "__main__":
    main()
