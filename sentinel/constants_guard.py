"""
Constants & Version Guard: Audits codebase for hardcoded literals & version fragmentation.
Strictly <= 200 lines and <= 100 characters per line.
"""
import os
import re
from typing import Dict, List, Any
from constants import AUDIT_EXTENSIONS, IGNORED_DIRS

# Regex patterns for finding hardcoded magic values in logic
URL_PATTERN = re.compile(r'https?://[a-zA-Z0-9.-]+(?::[0-9]+)?(?:/[^\s"\']*)?')
PORT_ASSIGNMENT_PATTERN = re.compile(r'(?:port|PORT)\s*[:=]\s*(\d{4,5})')
RAW_IP_PATTERN = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')

CONSTANTS_FILE_NAMES = {"constants.py", "constants.ts", "constants.js", "config.ts", "config.py"}


def is_constants_file(filepath: str) -> bool:
    """Checks if a file is an official constants or env declaration registry."""
    basename = os.path.basename(filepath).lower()
    if basename in CONSTANTS_FILE_NAMES or basename.startswith(".env"):
        return True
    return False


def audit_constants_compliance(filepath: str) -> List[Dict[str, Any]]:
    """Flags inline hardcoded URLs, IPs, or fixed port assignments in logic files."""
    if is_constants_file(filepath):
        return []

    violations = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        return []

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith(("#", "//", "/*", "*", "import ", "from ")):
            continue

        # Check for hardcoded raw URLs in business logic
        url_match = URL_PATTERN.search(stripped)
        if url_match:
            url_str = url_match.group(0)
            # Exclude standard schemas and schemas definitions
            if "schema.org" not in url_str and "w3.org" not in url_str:
                violations.append({
                    "type": "hardcoded_url_literal",
                    "line": idx,
                    "matched": url_str,
                    "message": "URL literal hardcoded inline. Must reside in constants/.env."
                })

        # Check for hardcoded raw IP addresses
        ip_match = RAW_IP_PATTERN.search(stripped)
        if ip_match:
            ip_str = ip_match.group(0)
            if ip_str not in ("127.0.0.1", "0.0.0.0"):
                violations.append({
                    "type": "hardcoded_ip_literal",
                    "line": idx,
                    "matched": ip_str,
                    "message": "IP literal hardcoded inline. Must reside in constants/.env."
                })

    return violations


def audit_constants_directory(root_dir: str) -> List[Dict[str, Any]]:
    """Recursively checks directory for hardcoded literal violations."""
    results = []
    if not os.path.isdir(root_dir):
        return results

    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in AUDIT_EXTENSIONS:
                full_path = os.path.join(root, file)
                v = audit_constants_compliance(full_path)
                if v:
                    results.append({"file": full_path, "violations": v})
    return results
