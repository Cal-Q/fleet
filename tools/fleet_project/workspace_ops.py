"""
Fleet Project Manager - Workspace & Git Repository Setup.
Strictly <= 200 lines.
"""

from typing import Tuple
from .ssh_helper import run_oracle, run_ionos

def create_workspace(project_id: str, username: str, title: str, desc: str) -> Tuple[bool, str]:
    clean_desc = desc.replace('"', '\\"')
    clean_title = title.replace('"', '\\"')
    ionos_script = f"""
set -e
mkdir -p /opt/{project_id}
chown -R {username}:{username} /opt/{project_id}
sudo -u {username} bash << 'GIT_INIT_EOF'
cd /opt/{project_id}
if [ ! -d .git ]; then
    git init -b main
    git config user.name '{username}'
    git config user.email '{username}@calq.it'

    cat << 'README_EOF' > README.md
# {clean_title}

{clean_desc}

## Overview
- **User**: `{username}`
- **Location**: `/opt/{project_id}` (IONOS) / `/mnt/workspaces/{project_id}` (Oracle VPS)
README_EOF

    cat << 'GITIGNORE_EOF' > .gitignore
__pycache__/
*.py[cod]
*\\$py.class
.venv/
env/
.pytest_cache/
*.log
*.sqlite3
*.db
.DS_Store
GITIGNORE_EOF

    ln -sfn /opt/master/.agents/rules/GLOBAL_AGENTS.md AGENTS.md
    mkdir -p .agents
    ln -sfn ../AGENTS.md .agents/AGENTS.md

    git add README.md .gitignore AGENTS.md .agents/AGENTS.md
    git commit -m 'feat: initial project scaffold'
fi
GIT_INIT_EOF
"""
    code_ion, _, err_ion = run_ionos(ionos_script)
    if code_ion != 0:
        return False, f"Failed to initialize repo on IONOS: {err_ion}"

    oracle_script = f"""
set -e
mkdir -p /mnt/workspaces/{project_id}
chown {username}:{username} /mnt/workspaces/{project_id}
chmod 755 /mnt/workspaces/{project_id}
ln -sfn /mnt/workspaces/{project_id} /opt/{project_id}
"""
    code_ora, _, err_ora = run_oracle(oracle_script)
    if code_ora != 0:
        return False, f"Failed to setup workspace mountpoint on Oracle: {err_ora}"

    return True, "Workspace created and symlinked successfully"

def delete_workspace(project_id: str, purge: bool = False) -> Tuple[bool, str]:
    oracle_script = f"""
fusermount3 -u -z /mnt/workspaces/{project_id} 2>/dev/null || true
rm -f /opt/{project_id}
rm -rf /mnt/workspaces/{project_id}
"""
    run_oracle(oracle_script)

    purge_flag = "true" if purge else "false"
    ionos_script = f"""
if [ "{purge_flag}" = "true" ]; then
    rm -rf /opt/{project_id}
else
    mkdir -p /opt/backups
    tar -czf /opt/backups/{project_id}-$(date +%s).tar.gz -C /opt {project_id} 2>/dev/null || true
    rm -rf /opt/{project_id}
fi
"""
    run_ionos(ionos_script)
    return True, f"Workspace for {project_id} removed"
