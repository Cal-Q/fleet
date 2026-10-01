"""
Central constants registry for Fleet Sentinel and Audit daemons.
Strictly <= 200 lines and <= 100 characters per line.
"""
from typing import List, Set

VERSION = "1.0.0"

# Audit Limits
MAX_SOURCE_LINES = 200
MAX_LINE_COLUMNS = 100

# File extensions subject to line and column limits
AUDIT_EXTENSIONS: Set[str] = {
    ".py", ".ts", ".js", ".tsx", ".jsx", ".html", ".css", ".sql", ".sh"
}

# Directories ignored during recursive audits
IGNORED_DIRS: Set[str] = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", "dist",
    "build", ".next", ".system_generated", "extracted", "logs", "etc",
    "usr", "var", "lib", "proc", "dev"
}

# Monitored workspace paths
MONITORED_WORKSPACES: List[str] = [
    "/mnt/workspaces/master",
    "/mnt/workspaces/japan",
    "/mnt/workspaces/fitness",
    "/mnt/workspaces/security",
    "/mnt/workspaces/vinted",
    "/mnt/workspaces/hub"
]

# Heartbeat endpoints & remote nodes
REMOTE_NODES = [
    {"name": "ionos", "host": "82.165.61.120", "ssh_alias": "ionos"},
    {"name": "contabo", "host": "169.58.70.214", "ssh_alias": "contabo"},
    {"name": "chromebook", "host": "127.0.0.1", "port": 2223, "type": "cockpit"}
]

# Filepaths for state & telemetry
STATE_DIR = "/var/lib/fleet-sentinel"
STATUS_JSON_PATH = "/var/lib/fleet-sentinel/status.json"
VIOLATIONS_JSON_PATH = "/var/lib/fleet-sentinel/violations.json"
HEARTBEAT_JSON_PATH = "/var/lib/fleet-sentinel/heartbeat.json"

# Loop intervals
DAEMON_INTERVAL_SECONDS = 30
SSH_TIMEOUT_SECONDS = 3
