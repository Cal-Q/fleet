#!/usr/bin/env python3
"""
Hub & AGY CLI Live Diagnostic & Monitor Tool
Usage:
  python3 hub_diag.py          # Quick one-shot diagnosis
  python3 hub_diag.py --watch  # Live 1s auto-refresh dashboard
Strictly <= 200 lines.
"""

import sys, os, time, json, subprocess

def run(cmd, timeout=5):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return 1, "", str(e)

def get_oracle_state():
    code, out, _ = run(["pgrep", "-f", "agy --dangerously-skip-permissions"])
    pids = out.split() if out else []
    act_file = "/home/master/.gemini/antigravity-cli/active_session.json"
    act_cid = None
    if os.path.exists(act_file):
        try:
            with open(act_file) as f: act_cid = json.load(f).get("conversation_id")
        except Exception: pass
    code, sync_st, _ = run(["sudo", "systemctl", "is-active", "agy-transcript-sync"])
    t_size, t_lines, last_type, last_time = 0, 0, None, None
    if act_cid:
        t_path = f"/home/master/.gemini/antigravity-cli/brain/{act_cid}/.system_generated/logs/transcript.jsonl"
        if os.path.exists(t_path):
            t_size = os.path.getsize(t_path)
            code, l_out, _ = run(["wc", "-l", t_path])
            t_lines = int(l_out.split()[0]) if l_out else 0
            code, tail_out, _ = run(["tail", "-n", "1", t_path])
            if tail_out:
                try:
                    d = json.loads(tail_out)
                    last_type = d.get("type")
                    last_time = d.get("created_at")
                except Exception: pass
    return {"pids": pids, "cid": act_cid, "sync_active": sync_st == "active",
            "t_size": t_size, "t_lines": t_lines, "last_type": last_type, "last_time": last_time}

def get_ionos_state(cid):
    code, st, _ = run(["ssh", "-o", "ConnectTimeout=3", "ionos", "sudo systemctl is-active gemini-hub"])
    hub_active = (st == "active")
    code, tmux_chk, _ = run(["ssh", "-o", "ConnectTimeout=3", "ionos", "sudo tmux has-session -t agy-master 2>&1"])
    has_tmux = (code == 0)
    busy = False
    pane_tail = ""
    if has_tmux:
        code, pane, _ = run(["ssh", "-o", "ConnectTimeout=3", "ionos", "sudo tmux capture-pane -p -t agy-master"])
        lines = pane.splitlines()[-8:] if pane else []
        pane_tail = "\n".join(lines)
        busy = any(k in pane_tail for k in ["esc to cancel", "Running command", "Thinking..."])
    ionos_size = 0
    if cid:
        cmd = f"sudo stat -c %s /home/master/.gemini/antigravity-cli/brain/{cid}/.system_generated/logs/transcript.jsonl 2>/dev/null || echo 0"
        code, sz_out, _ = run(["ssh", "-o", "ConnectTimeout=3", "ionos", cmd])
        try: ionos_size = int(sz_out.strip())
        except Exception: pass
    return {"hub_active": hub_active, "has_tmux": has_tmux, "busy": busy,
            "pane_tail": pane_tail, "ionos_size": ionos_size}

def render_state(o, i):
    os.system("clear" if sys.stdout.isatty() else "true")
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"=== CALQ HUB <-> AGY CLI SYNC DIAGNOSTIC [{now}] ===")
    print(f"▶ ORACLE VPS:")
    print(f"  AGY CLI PIDs   : {o['pids'] or 'None (idle/dead)'}")
    print(f"  Active Conv ID : {o['cid'] or 'None detected'}")
    print(f"  Sync Service   : {'✅ active' if o['sync_active'] else '❌ inactive'}")
    print(f"  Transcript     : {o['t_lines']} lines | {o['t_size']} bytes")
    print(f"  Last Entry     : {o['last_type']} ({o['last_time']})")
    print(f"\n▶ IONOS WEB SERVER:")
    print(f"  gemini-hub     : {'✅ active' if i['hub_active'] else '❌ inactive'}")
    print(f"  agy-master tmux: {'✅ present' if i['has_tmux'] else '❌ missing'}")
    print(f"  Agent Busy     : {'🔴 BUSY (turn running)' if i['busy'] else '🟢 IDLE (waiting for prompt)'}")
    delta = o['t_size'] - i['ionos_size']
    delta_str = "✅ in sync (0 byte lag)" if delta == 0 else f"⚠️ {delta} bytes lag"
    print(f"  Synced Size    : {i['ionos_size']} bytes [{delta_str}]")
    print(f"\n▶ TMUX PANE TAIL:")
    for line in i['pane_tail'].splitlines()[-4:]:
        print(f"  | {line}")
    print("=" * 55)

def main():
    watch_mode = "--watch" in sys.argv
    while True:
        o = get_oracle_state()
        i = get_ionos_state(o["cid"])
        render_state(o, i)
        if not watch_mode: break
        time.sleep(1)

if __name__ == "__main__":
    main()
