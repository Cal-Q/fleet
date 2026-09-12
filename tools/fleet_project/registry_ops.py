"""
Fleet Project Manager - Fleet & Hub Registration Operations.
Strictly <= 200 lines.
"""

import os
import re
from typing import Tuple
from .ssh_helper import run_ionos

def register_in_hub(project_id: str, username: str, title: str, icon: str, desc: str) -> bool:
    hub_script = (
        'python3 -c "\n'
        'import os\n'
        'cfg = \\"/opt/hub/core/config.py\\"\n'
        'if os.path.exists(cfg):\n'
        '    with open(cfg, \\"r\\") as f:\n'
        '        text = f.read()\n'
        f'    if \\"{project_id}\\" not in text:\n'
        f'        block = \'\'\'    {{\\n'
        f'        \\"id\\": \\"{project_id}\\",\\n'
        f'        \\"name\\": \\"{title}\\",\\n'
        f'        \\"icon\\": \\"{icon}\\",\\n'
        f'        \\"user\\": \\"{username}\\",\\n'
        f'        \\"host\\": \\"ionos\\",\\n'
        f'        \\"path\\": \\"/opt/{project_id}\\",\\n'
        f'        \\"desc\\": \\"{desc}\\",\\n'
        f'    }},\\n\'\'\'\n'
        '        target = \'    {\\n        \\"id\\": \\"oracle-worker\\",\'\n'
        '        if target in text:\n'
        '            text = text.replace(target, block + target)\n'
        '            with open(cfg, \\"w\\") as f:\n'
        '                f.write(text)\n'
        '"'
    )
    code, _, _ = run_ionos(hub_script)
    return code == 0

def register_in_fleet_tools(project_id: str, username: str, title: str) -> bool:
    script = (
        'set -e\n'
        'cd /opt/master\n'
        f'if ! grep -q "{project_id}|.*) echo \\"{username} /opt/{project_id}\\"" tools/attach-agy; then\n'
        f'    sed -i \'/case "\\$1" in/a \\        {project_id}) echo "{username} /opt/{project_id}" ;;\' tools/attach-agy\n'
        'fi\n'
        f'if ! grep -q \'"/opt/{project_id}"\' tools/status.py; then\n'
        f'    sed -i \'/PROJECTS = \\[/a \\    ("{title}", "{username}", "/opt/{project_id}", []),\' tools/status.py\n'
        'fi\n'
        f'if ! grep -q \'"/opt/{project_id}"\' tools/git_overview.py; then\n'
        f'    sed -i \'/REPOS = \\[/a \\    ("{title}", "/opt/{project_id}"),\' tools/git_overview.py\n'
        'fi\n'
        f'if ! grep -q \'/opt/{project_id}\' AGENTS.md; then\n'
        f'    sed -i "/FLEET REPOSITORY LOCATIONS:/a \\   - {title}: \\`/opt/{project_id}\\` (User: \\`{username}\\`)" AGENTS.md\n'
        'fi\n'
        f'if [ -f .agents/AGENTS.md ] && ! grep -q \'/opt/{project_id}\' .agents/AGENTS.md; then\n'
        f'    sed -i "/FLEET REPOSITORY LOCATIONS:/a \\   - {title}: \\`/opt/{project_id}\\` (User: \\`{username}\\`)" .agents/AGENTS.md\n'
        'fi\n'
        'git add tools/attach-agy tools/status.py tools/git_overview.py AGENTS.md .agents/AGENTS.md 2>/dev/null || true\n'
        f'git commit -m "feat(fleet): register {project_id} in fleet tools" 2>/dev/null || true\n'
    )
    code, _, _ = run_ionos(script)
    return code == 0

def register_all(project_id: str, username: str, title: str, icon: str, desc: str) -> Tuple[bool, str]:
    ok_hub = register_in_hub(project_id, username, title, icon, desc)
    ok_fleet = register_in_fleet_tools(project_id, username, title)
    if not (ok_hub and ok_fleet):
        return False, "Failed to complete all registrations"
    return True, "Project successfully registered in Hub and Fleet tools"

def unregister_all(project_id: str) -> Tuple[bool, str]:
    script = (
        'python3 -c "\n'
        'import os, re\n'
        'cfg = \\"/opt/hub/core/config.py\\"\n'
        'if os.path.exists(cfg):\n'
        '    with open(cfg, \\"r\\") as f:\n'
        '        text = f.read()\n'
        f'    pat = r\'\\s*\\{{\\s*\\"id\\":\\s*\\"{project_id}\\",.*?\\n\\s*\\}},?\'\n'
        '    new_text = re.sub(pat, \'\', text, flags=re.DOTALL)\n'
        '    if new_text != text:\n'
        '        with open(cfg, \\"w\\") as f:\n'
        '            f.write(new_text)\n'
        '" 2>/dev/null || true\n'
        'cd /opt/master\n'
        f'sed -i \'/{project_id}) echo/d\' tools/attach-agy 2>/dev/null || true\n'
        f'sed -i \'/\\/opt\\/{project_id}/d\' tools/status.py 2>/dev/null || true\n'
        f'sed -i \'/\\/opt\\/{project_id}/d\' tools/git_overview.py 2>/dev/null || true\n'
        f'sed -i \'/\\/opt\\/{project_id}/d\' AGENTS.md 2>/dev/null || true\n'
        f'[ -f .agents/AGENTS.md ] && sed -i \'/\\/opt\\/{project_id}/d\' .agents/AGENTS.md 2>/dev/null || true\n'
        'git add tools/attach-agy tools/status.py tools/git_overview.py AGENTS.md .agents/AGENTS.md 2>/dev/null || true\n'
        f'git commit -m "chore(fleet): unregister {project_id} from fleet tools" 2>/dev/null || true\n'
    )
    run_ionos(script)
    return True, f"Unregistered {project_id} from Hub and Fleet tools"
