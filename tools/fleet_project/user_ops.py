"""
Fleet Project Manager - System User & Sudoers Operations.
Strictly <= 200 lines.
"""

from typing import Tuple, Optional
from .ssh_helper import run_oracle, run_ionos, get_passwd_uids

def allocate_uid_gid(min_uid: int = 2014) -> int:
    used_oracle = get_passwd_uids(on_oracle=True)
    used_ionos = get_passwd_uids(on_oracle=False)
    candidate = min_uid
    while candidate in used_oracle or candidate in used_ionos:
        candidate += 1
    return candidate

def user_exists(username: str) -> bool:
    c1, _, _ = run_oracle(f"id {username}")
    c2, _, _ = run_ionos(f"id {username}")
    return c1 == 0 or c2 == 0

def create_user(username: str, uid: int, gid: int) -> Tuple[bool, str]:
    script = f"""
set -e
if ! getent group {gid} >/dev/null; then
    groupadd -g {gid} {username}
fi
if ! id {username} >/dev/null 2>&1; then
    useradd -u {uid} -g {gid} -m -s /bin/bash {username}
fi
chmod 750 /home/{username}
"""
    c_ora, _, e_ora = run_oracle(script)
    if c_ora != 0:
        return False, f"Failed to create user on Oracle: {e_ora}"

    c_ion, _, e_ion = run_ionos(script)
    if c_ion != 0:
        return False, f"Failed to create user on IONOS: {e_ion}"

    return True, "User created successfully"

def setup_sudoers(username: str) -> Tuple[bool, str]:
    script = f"""
set -e
echo '{username} ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/{username}-unrestricted
chmod 0440 /etc/sudoers.d/{username}-unrestricted
"""
    c_ora, _, e_ora = run_oracle(script)
    if c_ora != 0:
        return False, f"Failed to set sudoers on Oracle: {e_ora}"

    c_ion, _, e_ion = run_ionos(script)
    if c_ion != 0:
        return False, f"Failed to set sudoers on IONOS: {e_ion}"

    return True, "Sudoers configured successfully"

def delete_user(username: str) -> Tuple[bool, str]:
    script = f"""
pkill -9 -u {username} 2>/dev/null || true
rm -f /etc/sudoers.d/{username}-unrestricted
userdel -r -f {username} 2>/dev/null || true
"""
    run_oracle(script)
    run_ionos(script)
    return True, f"User {username} deleted"
