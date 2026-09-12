"""
Fleet Project Manager - SSH Key & Gemini Profile Setup.
Strictly <= 200 lines.
"""

from typing import Tuple
from .ssh_helper import run_oracle, run_ionos

def setup_ssh_keys(username: str) -> Tuple[bool, str]:
    oracle_gen_script = f"""
set -e
mkdir -p /home/{username}/.ssh
chmod 700 /home/{username}/.ssh
if [ ! -f /home/{username}/.ssh/id_ed25519_agent ]; then
    ssh-keygen -q -t ed25519 -N "" -f /home/{username}/.ssh/id_ed25519_agent -C "{username}@vps-arm-ubuntu" >/dev/null 2>&1
fi
if [ -f /home/phonemigrate/.ssh/config ]; then
    cp /home/phonemigrate/.ssh/config /home/{username}/.ssh/config
    sed -i '/Host ionos/,+5 s/User .*/User {username}/' /home/{username}/.ssh/config
    chmod 600 /home/{username}/.ssh/config
fi
ssh-keyscan -H 82.165.61.120 > /home/{username}/.ssh/known_hosts 2>/dev/null || true
chmod 644 /home/{username}/.ssh/known_hosts
chown -R {username}:{username} /home/{username}/.ssh
cat /home/{username}/.ssh/id_ed25519_agent.pub
"""
    code, raw_out, err = run_oracle(oracle_gen_script)
    if code != 0:
        return False, f"Failed to generate SSH key on Oracle: {err}"

    clean_pubkey = ""
    for line in raw_out.splitlines():
        line = line.strip()
        if line.startswith("ssh-"):
            clean_pubkey = line
            break

    if not clean_pubkey:
        return False, f"Could not find valid public key in output: {raw_out}"

    ionos_auth_script = f"""
set -e
mkdir -p /home/{username}/.ssh
chmod 700 /home/{username}/.ssh
echo '{clean_pubkey}' > /home/{username}/.ssh/authorized_keys
chmod 600 /home/{username}/.ssh/authorized_keys
chown -R {username}:{username} /home/{username}/.ssh
"""
    code_ion, _, err_ion = run_ionos(ionos_auth_script)
    if code_ion != 0:
        return False, f"Failed to install authorized_keys on IONOS: {err_ion}"

    return True, "SSH key pair generated and authorized"

def setup_gemini_profile(username: str, project_id: str) -> Tuple[bool, str]:
    token_src = "/home/phonemigrate/.gemini/antigravity-cli/antigravity-oauth-token"
    script = f"""
set -e
mkdir -p /home/{username}/.gemini/antigravity-cli
mkdir -p /home/{username}/.gemini/config/skills
mkdir -p /home/{username}/.gemini/config/projects
if [ -f '{token_src}' ]; then
    cp '{token_src}' /home/{username}/.gemini/antigravity-cli/antigravity-oauth-token
    chmod 600 /home/{username}/.gemini/antigravity-cli/antigravity-oauth-token
fi
cat << 'SETTINGS_EOF' > /home/{username}/.gemini/antigravity-cli/settings.json
{{
  "colorScheme": "dark",
  "trustedWorkspaces": [
    "/mnt/workspaces/{project_id}"
  ]
}}
SETTINGS_EOF
if [ -d '/opt/master/.agents/skills' ]; then
    for s in /opt/master/.agents/skills/*; do
        [ -d "$s" ] || continue
        ln -sfn "$s" "/home/{username}/.gemini/config/skills/$(basename "$s")" 2>/dev/null || true
    done
fi
if [ -f '/opt/master/.agents/rules/GLOBAL_AGENTS.md' ]; then
    ln -sfn '/opt/master/.agents/rules/GLOBAL_AGENTS.md' "/home/{username}/.gemini/config/AGENTS.md"
fi
chown -h -R {username}:{username} /home/{username}/.gemini
"""
    c_ora, _, e_ora = run_oracle(script)
    if c_ora != 0:
        return False, f"Failed to setup Gemini profile on Oracle: {e_ora}"

    c_ion, _, e_ion = run_ionos(script)
    if c_ion != 0:
        return False, f"Failed to setup Gemini profile on IONOS: {e_ion}"

    return True, "Gemini profile and credentials initialized"
