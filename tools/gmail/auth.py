#!/usr/bin/env python3
"""Gmail OAuth Authentication Module for Master Agent."""

import os
import subprocess
import sys
import time
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

CRED_DIR = Path(os.path.expanduser("~/.config/gmail"))
CREDENTIALS_FILE = CRED_DIR / "credentials.json"
TOKEN_FILE = CRED_DIR / "token.json"

SCOPES = [
    "https://mail.google.com/",
]

PORT = 8085


def start_reverse_tunnel(port: int = PORT) -> subprocess.Popen:
    """Start reverse SSH tunnel from chromebook:port to localhost:port."""
    cmd = [
        "ssh",
        "-o", "ExitOnForwardFailure=yes",
        "-o", "StrictHostKeyChecking=no",
        "-R", f"{port}:localhost:{port}",
        "chromebook",
        "sleep", "300"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    time.sleep(2)
    if proc.poll() is not None:
        stderr = proc.stderr.read().decode() if proc.stderr else ""
        print(f"[WARN] Failed to start reverse tunnel to chromebook: {stderr}")
    else:
        print(f"[INFO] Reverse tunnel active: chromebook:{port} -> localhost:{port}")
    return proc


def authenticate():
    """Run OAuth2 flow and save token.json."""
    if not CREDENTIALS_FILE.exists():
        print(f"[ERROR] Credentials file not found at {CREDENTIALS_FILE}", file=sys.stderr)
        sys.exit(1)

    tunnel_proc = start_reverse_tunnel(PORT)
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_FILE),
            scopes=SCOPES
        )

        print("\n" + "=" * 60)
        print("GMAIL AUTHORIZATION NEEDED")
        print("Please visit this URL in your browser to authorize access:")
        print("=" * 60)

        creds = flow.run_local_server(
            host="localhost",
            port=PORT,
            open_browser=False,
            access_type="offline",
            prompt="consent"
        )

        CRED_DIR.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(creds.to_json())
        TOKEN_FILE.chmod(0o600)
        print("\n[SUCCESS] Authentication successful! Token saved to", TOKEN_FILE)
        return creds
    finally:
        if tunnel_proc and tunnel_proc.poll() is None:
            tunnel_proc.terminate()
            tunnel_proc.wait()
            print("[INFO] Reverse tunnel closed.")


if __name__ == "__main__":
    authenticate()
