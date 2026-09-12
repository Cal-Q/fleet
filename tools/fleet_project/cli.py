#!/usr/bin/env python3
"""
Fleet Project Manager - Unified CLI.
Strictly <= 200 lines.
"""

import sys
import os
import time
import argparse
import re

if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from fleet_project import user_ops, auth_ops, workspace_ops, registry_ops
else:
    from . import user_ops, auth_ops, workspace_ops, registry_ops

def infer_icon(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ["card", "yugi", "poke"]): return "🃏"
    if any(k in n for k in ["transcri", "whisper", "speech", "audio"]): return "🎙️"
    if any(k in n for k in ["sniper", "deal", "market"]): return "🎯"
    if any(k in n for k in ["game", "play", "bot"]): return "🎮"
    if any(k in n for k in ["phone", "mobile", "android"]): return "📱"
    if any(k in n for k in ["study", "mext", "learn", "tutor"]): return "📚"
    return "⚡"

def handle_create(args: argparse.Namespace) -> int:
    pid = args.project_id.strip().lower()
    if not re.match(r"^[a-z0-9_-]+$", pid):
        print(f"Error: Invalid project ID '{pid}'. Use lowercase alphanumeric, hyphens, underscores.")
        return 1

    username = (args.user or pid).strip().lower()
    title = args.title or pid.replace("-", " ").replace("_", " ").title()
    icon = args.icon or infer_icon(title)
    desc = args.desc or f"{title} Project Workspace & Agent"

    if user_ops.user_exists(username):
        print(f"Error: User '{username}' already exists on Oracle VPS or IONOS.")
        return 1

    start_time = time.time()
    print(f"\n🚀 Creating fleet project: {title} [{pid}] (user: {username})")

    # 1. Allocate UID/GID
    uid = user_ops.allocate_uid_gid()
    print(f"  [1/6] Allocated UID/GID: {uid}")

    # 2. System User & Sudoers
    ok, msg = user_ops.create_user(username, uid, uid)
    if not ok: print(f"  [-] {msg}"); return 1
    ok, msg = user_ops.setup_sudoers(username)
    if not ok: print(f"  [-] {msg}"); return 1
    print("  [2/6] User & passwordless sudo configured on Oracle VPS & IONOS")

    # 3. SSH Keys
    ok, msg = auth_ops.setup_ssh_keys(username)
    if not ok: print(f"  [-] {msg}"); return 1
    print("  [3/6] Agent ed25519 SSH keys authorized")

    # 4. Gemini Profile & OAuth
    ok, msg = auth_ops.setup_gemini_profile(username, pid)
    if not ok: print(f"  [-] {msg}"); return 1
    print("  [4/6] Gemini profile & active OAuth credentials linked")

    # 5. Workspace & Git Repo
    ok, msg = workspace_ops.create_workspace(pid, username, title, desc)
    if not ok: print(f"  [-] {msg}"); return 1
    print(f"  [5/6] Git repo initialized on IONOS (/opt/{pid}) and linked on Oracle (/opt/{pid})")

    # 6. Fleet & Hub Registration (Hot-reloaded, ZERO downtime!)
    ok, msg = registry_ops.register_all(pid, username, title, icon, desc)
    if not ok: print(f"  [-] {msg}"); return 1
    print("  [6/6] Registered in Master Hub (calq.it/console/), attach-agy, and fleet docs")

    dur = time.time() - start_time
    print(f"\n✨ Project '{pid}' created successfully in {dur:.1f}s!")
    print(f"   Console:   https://calq.it/console/ (Live, zero disconnects)")
    print(f"   Terminal:  attach-agy {pid}")
    print(f"   Workspace: /opt/{pid} -> /mnt/workspaces/{pid}\n")
    return 0

def handle_delete(args: argparse.Namespace) -> int:
    pid = args.project_id.strip().lower()
    username = (args.user or pid).strip().lower()

    print(f"\n🗑️  Deleting fleet project: {pid} (user: {username})")
    start_time = time.time()

    # 1. Unregister from tools and Hub
    registry_ops.unregister_all(pid)
    print("  [1/3] Unregistered from Master Hub, attach-agy, and fleet docs")

    # 2. Workspace cleanup
    workspace_ops.delete_workspace(pid, purge=args.purge)
    action_str = "purged" if args.purge else "archived to /opt/backups/"
    print(f"  [2/3] Workspace {action_str}")

    # 3. User & Sudoers cleanup
    user_ops.delete_user(username)
    print("  [3/3] User accounts and sudoers removed from both servers")

    dur = time.time() - start_time
    print(f"\n✨ Project '{pid}' completely removed in {dur:.1f}s!\n")
    return 0

def main():
    parser = argparse.ArgumentParser(description="Fleet Project & User Manager")
    sub = parser.add_subparsers(dest="action", required=True)

    c_parser = sub.add_parser("create", help="Create new user, repo, workspace & hub entry")
    c_parser.add_argument("project_id", help="Unique project slug (e.g. digimon)")
    c_parser.add_argument("--user", help="Custom username (defaults to project_id)")
    c_parser.add_argument("--title", help="Human-readable title")
    c_parser.add_argument("--icon", help="Display emoji icon")
    c_parser.add_argument("--desc", help="Short description")

    d_parser = sub.add_parser("delete", help="Delete user, workspace & hub entry")
    d_parser.add_argument("project_id", help="Project ID to delete")
    d_parser.add_argument("--user", help="Username if different from project_id")
    d_parser.add_argument("--purge", action="store_true", help="Permanently delete files instead of backup archive")

    args = parser.parse_args()
    if args.action == "create":
        sys.exit(handle_create(args))
    elif args.action == "delete":
        sys.exit(handle_delete(args))

if __name__ == "__main__":
    main()
