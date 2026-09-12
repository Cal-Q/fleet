"""
Fleet Project Manager - Unified Cross-Host Execution Helper.
Strictly <= 200 lines.
"""

import os
import base64
import socket
import subprocess
from typing import Tuple, Set

ORACLE_IP = "84.8.254.222"
ORACLE_USER = "ubuntu"
IONOS_ALIAS = "ionos"

def is_oracle_host() -> bool:
    return os.path.exists("/usr/local/bin/launch-oracle-agent") or socket.gethostname() == "vps-arm-ubuntu"

def run_bash_cmd(cmd_list, timeout: int = 30) -> Tuple[int, str, str]:
    try:
        res = subprocess.run(cmd_list, capture_output=True, text=True, timeout=timeout)
        return res.returncode, res.stdout, res.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)

def run_oracle(bash_script: str, timeout: int = 30) -> Tuple[int, str, str]:
    b64 = base64.b64encode(bash_script.encode("utf-8")).decode("ascii")
    if is_oracle_host():
        cmd = ["sudo", "bash", "-c", f"echo {b64} | base64 -d | bash"]
    else:
        cmd = [
            "ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
            f"{ORACLE_USER}@{ORACLE_IP}",
            f"echo {b64} | base64 -d | sudo bash"
        ]
    return run_bash_cmd(cmd, timeout)

def run_ionos(bash_script: str, timeout: int = 30) -> Tuple[int, str, str]:
    b64 = base64.b64encode(bash_script.encode("utf-8")).decode("ascii")
    if not is_oracle_host():
        cmd = ["sudo", "bash", "-c", f"echo {b64} | base64 -d | bash"]
    else:
        cmd = [
            "ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
            IONOS_ALIAS,
            f"echo {b64} | base64 -d | sudo bash"
        ]
    return run_bash_cmd(cmd, timeout)

def get_passwd_uids(on_oracle: bool = True) -> Set[int]:
    script = "awk -F: '{print $3}' /etc/passwd /etc/group"
    code, out, _ = run_oracle(script) if on_oracle else run_ionos(script)
    uids = set()
    if code == 0:
        for line in out.splitlines():
            line = line.strip()
            if line.isdigit():
                uids.add(int(line))
    return uids
