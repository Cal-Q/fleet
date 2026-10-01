"""
Connectivity Guard: Verifies connectivity to Oracle, IONOS, Contabo & Chromebook.
Strictly <= 200 lines and <= 100 characters per line.
"""
import subprocess
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List
from constants import REMOTE_NODES, SSH_TIMEOUT_SECONDS


def check_ssh_node(alias: str) -> Dict[str, Any]:
    """Tests SSH ping with strict timeout."""
    t0 = time.time()
    cmd = [
        "timeout", f"{SSH_TIMEOUT_SECONDS}s",
        "ssh", "-o", f"ConnectTimeout={SSH_TIMEOUT_SECONDS}",
        "-o", "BatchMode=yes",
        alias, "echo pong"
    ]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        elapsed = round((time.time() - t0) * 1000, 2)
        alive = (proc.returncode == 0 and "pong" in proc.stdout)
        return {
            "node": alias,
            "alive": alive,
            "latency_ms": elapsed if alive else None,
            "error": proc.stderr.strip() if not alive else None
        }
    except Exception as err:
        return {"node": alias, "alive": False, "latency_ms": None, "error": str(err)}


def check_socket_port(host: str, port: int) -> Dict[str, Any]:
    """Tests socket reachability (e.g. Chromebook port 2223)."""
    t0 = time.time()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(SSH_TIMEOUT_SECONDS)
    try:
        sock.connect((host, port))
        sock.close()
        elapsed = round((time.time() - t0) * 1000, 2)
        return {"host": host, "port": port, "alive": True, "latency_ms": elapsed}
    except Exception as err:
        return {"host": host, "port": port, "alive": False, "error": str(err)}


def _probe_single(node: dict) -> Dict[str, Any]:
    if node.get("type") == "cockpit":
        res = check_socket_port(node["host"], node["port"])
        res["name"] = node["name"]
        return res
    if "ssh_alias" in node:
        res = check_ssh_node(node["ssh_alias"])
        res["name"] = node["name"]
        return res
    return {"name": node.get("name", "unknown"), "alive": False}


def audit_fleet_connectivity() -> List[Dict[str, Any]]:
    """Checks all nodes concurrently in parallel."""
    with ThreadPoolExecutor(max_workers=len(REMOTE_NODES)) as executor:
        return list(executor.map(_probe_single, REMOTE_NODES))

