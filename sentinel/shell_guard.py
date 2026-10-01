#!/usr/bin/env python3
"""
Shell Guard: PreToolUse hook preventing file mutations via shell redirects/scripts.
Strictly <= 200 lines and <= 100 characters per line.
"""
import sys
import json
import re
from typing import Tuple

TARGET_EXTENSIONS = (
    r'\.(?:py|ts|js|tsx|jsx|html|css|json|yaml|yml|md|sh|conf|sql|toml)\b'
)

# Detect file redirection (> or >> or | tee) targeting source or doc files
REDIRECT_PATTERN = re.compile(
    r'(?:>>|>|\|\s*tee(?:\s+-a)?)\s+([^\s;&|]+\b' + TARGET_EXTENSIONS + r')',
    re.IGNORECASE
)

# Detect inline python writing scripts
PYTHON_INLINE_WRITE_PATTERN = re.compile(
    r'python[23]?\s+-c\s+["\'].*(?:open\(.*,\s*["\']w\+?a?["\']|\.write\().*["\']',
    re.IGNORECASE
)


def inspect_command(command_line: str) -> Tuple[bool, str]:
    """Inspects a shell command for deterministic editing violations."""
    if not command_line:
        return True, ""

    redirect_match = REDIRECT_PATTERN.search(command_line)
    if redirect_match:
        target = redirect_match.group(1)
        reason = (
            f"Rule 4 Violation: Shell redirection into '{target}' is strictly forbidden. "
            "Use write_to_file or replace_file_content."
        )
        return False, reason

    if PYTHON_INLINE_WRITE_PATTERN.search(command_line):
        reason = (
            "Rule 4 Violation: Modifying files via inline python3 -c is strictly forbidden. "
            "Use write_to_file or replace_file_content."
        )
        return False, reason

    return True, ""


def main():
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({"decision": "allow"}))
            return

        payload = json.loads(raw_input)
        tool_call = payload.get("toolCall", {})
        tool_name = tool_call.get("name", "")
        args = tool_call.get("args", {})

        if tool_name == "run_command":
            cmd = args.get("CommandLine", "")
            allowed, reason = inspect_command(cmd)
            if not allowed:
                print(json.dumps({"decision": "deny", "reason": reason}))
                return

        print(json.dumps({"decision": "allow"}))
    except Exception:
        # Fallback to allow on unexpected parsing errors to prevent complete agent lock
        print(json.dumps({"decision": "allow"}))


if __name__ == "__main__":
    main()
