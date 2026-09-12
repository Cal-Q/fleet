#!/usr/bin/env python3
"""Master Status: Health and service monitor across all projects."""
import os
import json
import time
import shutil
import subprocess

PROJECTS = [
    ("Japan • Studies & Mastery", "japan", "/opt/japan", []),
    ("Fitness", "fitness", "/opt/fitness", []),
    ("Flying Thoughts and Considerations", "thoughts", "/opt/thoughts", [3040]),
    ("PokeVault", "pokeuser", "/opt/pokevault", [5000, 8000]),
    ("SSBU", "ssbu_brain", "/home/ssbu_brain/app", [4200, 8888, 8889, 55123]),
    ("MarketplaceSniper", "marketsniper", "/opt/marketplace-sniper", []),
    ("Bunpro Anki", "bunkibot", "/opt/bunpro-anki", [3001]),
    ("Remote Print", "printbot", "/opt/remote-print", [631]),
    ("Tutor", "tutor", "/home/tutor", []),
    ("JP Transcribe", "jptranscriber", "/home/jptranscriber", []),
    ("Gen Transcribe", "gentranscriber", "/opt/general-transcriber", [8877]),
    ("Sinoia Gang", "SinoiaGang", "/home/SinoiaGang", []),
    ("Road to MEXT", "mext", "/opt/road-to-mext", []),
    ("PhoneMigrate", "phonemigrate", "/opt/phone-migrate", []),
]

def check_git(path):
    if not os.path.exists(os.path.join(path, ".git")):
        return "no-git"
    try:
        res = subprocess.run(
            ["git", "-C", path, "status", "--porcelain"],
            capture_output=True, text=True, timeout=8
        )
        lines = res.stdout.strip().splitlines()
        return f"{len(lines)} uncommitted" if lines else "clean"
    except Exception:
        return "err"

def get_listening_ports():
    try:
        res = subprocess.run(["ss", "-tulpn"], capture_output=True, text=True, timeout=8)
        return res.stdout
    except Exception:
        return ""

def get_timers():
    path = "/var/lib/agy-accounts/user_timers.json"
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}

def main():
    print("=" * 75)
    print("                👑 MASTER HUB // FLEET & PROJECT STATUS                 ")
    print("=" * 75)

    total, used, free = shutil.disk_usage("/")
    print(f"[System Disk]  Total: {total//(1024**3)} GB | Used: {used//(1024**3)} GB | Free: {free//(1024**3)} GB")

    with open("/proc/meminfo") as f:
        mem = {line.split(":")[0]: int(line.split(":")[1].split()[0]) for line in f if ":" in line}
    ram_used = (mem.get("MemTotal", 0) - mem.get("MemAvailable", 0)) // 1024
    ram_total = mem.get("MemTotal", 0) // 1024
    print(f"[System RAM]   {ram_used} MB / {ram_total} MB used ({100*ram_used//max(1, ram_total)}%)")

    ports_dump = get_listening_ports()
    timers = get_timers()
    now = time.time()

    print("-" * 75)
    print(f"{'PROJECT':<18} {'USER':<13} {'GIT':<15} {'PORTS / DAEMONS':<16} {'TIMER'}")
    print("-" * 75)

    for name, user, path, expected_ports in PROJECTS:
        git_st = check_git(path)
        port_statuses = []
        for p in expected_ports:
            status = "🟢" if f":{p} " in ports_dump else "🔴"
            port_statuses.append(f"{status}:{p}")
        ports_str = " ".join(port_statuses) if port_statuses else "-"

        t_rem = timers.get(user, 0) - now
        timer_str = f"⏳ {int(t_rem//60)}m" if t_rem > 0 else "-"

        print(f"{name:<18} {user:<13} {git_st:<15} {ports_str:<16} {timer_str}")

    print("=" * 75)

if __name__ == "__main__":
    main()
