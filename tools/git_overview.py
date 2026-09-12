#!/usr/bin/env python3
"""Master Git Overview: Inspect branches and commits across all projects."""
import os
import subprocess

REPOS = [
    ("Japan • Studies & Mastery", "/opt/japan"),
    ("Fitness", "/opt/fitness"),
    ("Flying Thoughts and Considerations", "/opt/thoughts"),
    ("PokeVault", "/opt/pokevault"),
    ("SSBU", "/home/ssbu_brain/app"),
    ("MarketplaceSniper", "/opt/marketplace-sniper"),
    ("Bunpro Anki", "/opt/bunpro-anki"),
    ("Remote Print", "/opt/remote-print"),
    ("Road to MEXT", "/opt/road-to-mext"),
    ("PhoneMigrate", "/opt/phone-migrate"),
    ("General Transcriber", "/opt/general-transcriber"),
]

def run_git(path, args):
    try:
        res = subprocess.run(
            ["git", "-C", path] + args,
            capture_output=True, text=True, timeout=3
        )
        return res.stdout.strip()
    except Exception as e:
        return f"ERR: {e}"

def main():
    print("=" * 75)
    print("                 👑 MASTER HUB // GIT REPOSITORIES                      ")
    print("=" * 75)

    for name, path in REPOS:
        if not os.path.exists(os.path.join(path, ".git")):
            continue
        branch = run_git(path, ["rev-parse", "--abbrev-ref", "HEAD"])
        last_commit = run_git(path, ["log", "-1", "--format=%h %s (%cr)"])
        dirty = run_git(path, ["status", "--porcelain"])
        status_tag = "🧹 Clean" if not dirty else f"⚠️ {len(dirty.splitlines())} modified"

        print(f"[{name}]  Branch: {branch}  •  {status_tag}")
        print(f"   Last: {last_commit}")
        print(f"   Path: {path}")
        print("-" * 75)

if __name__ == "__main__":
    main()
