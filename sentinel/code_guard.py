"""
Code Quality Guard: Audits source files for lines <= 200, chars <= 100, and no semicolons.
Strictly <= 200 lines and <= 100 characters per line.
"""
import os
from typing import Dict, List, Any
from constants import (
    MAX_SOURCE_LINES,
    MAX_LINE_COLUMNS,
    AUDIT_EXTENSIONS,
    IGNORED_DIRS
)


def audit_file(filepath: str) -> Dict[str, Any]:
    """Audits a single source file against fleet modularity rules."""
    violations = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as err:
        return {"file": filepath, "error": str(err), "violations": []}

    total_lines = len(lines)
    if total_lines > MAX_SOURCE_LINES:
        violations.append({
            "type": "max_lines_exceeded",
            "message": f"File has {total_lines} lines (max allowed is {MAX_SOURCE_LINES})"
        })

    for idx, line in enumerate(lines, start=1):
        clean_line = line.rstrip("\r\n")
        # Ignore unbreakable URLs or base64 strings in comments
        if len(clean_line) > MAX_LINE_COLUMNS:
            if "http://" not in clean_line and "https://" not in clean_line:
                violations.append({
                    "type": "max_column_exceeded",
                    "line": idx,
                    "length": len(clean_line),
                    "snippet": clean_line[:80] + "..."
                })

        # Semicolon chaining check for Python/JS/TS
        if ";" in clean_line and not clean_line.strip().startswith(("#", "//", "/*", "*")):
            # Check if it chains multiple statements
            parts = [p.strip() for p in clean_line.split(";") if p.strip()]
            if len(parts) > 1 and not clean_line.strip().startswith("for "):
                violations.append({
                    "type": "semicolon_chaining",
                    "line": idx,
                    "snippet": clean_line
                })

    return {
        "file": filepath,
        "total_lines": total_lines,
        "violations": violations,
        "passed": len(violations) == 0
    }


def audit_directory(root_dir: str) -> List[Dict[str, Any]]:
    """Recursively audits all matching files in a directory."""
    results = []
    if not os.path.isdir(root_dir):
        return results

    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in AUDIT_EXTENSIONS:
                full_path = os.path.join(root, file)
                res = audit_file(full_path)
                if not res["passed"]:
                    results.append(res)
    return results
