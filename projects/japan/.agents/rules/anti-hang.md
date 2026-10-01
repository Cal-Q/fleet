# Predator Development Node Environment Directives

## Fleet Roles & Topology
- **Predator (calq-Predator-PHN16-71)**: Primary Development Server. All active projects, AGY workflows, code development, and tests run here natively in `~/workspaces/` with NVMe speed.
- **IONOS (82.165.61.120)**: Production & Relay Server. Reserved for lightweight, optimized production services and public endpoints. SSH alias: `ssh ionos`.
- **Oracle Cloud (84.8.254.222)**: Cloud VPS node. SSH alias: `ssh oracle`.

## Remote Access
- You have direct, passwordless SSH access to Oracle: `ssh oracle '<command>'`
- You have direct, passwordless SSH access to IONOS: `ssh ionos '<command>'`
- All conversation histories, SQLite databases, and brain transcripts from Oracle have been synced to `~/.gemini/antigravity-cli/conversations/` and `~/.gemini/antigravity-cli/brain/`.

## Command Execution & Anti-Hang Invariants
- **Strict Command Timeouts**: Every network, remote SSH, or external command MUST be wrapped in a hard local timeout (e.g. `timeout 5s ssh -o ConnectTimeout=3 ...`).
- **Never Run Interactive or Indefinite Commands**: Avoid commands that prompt for input, allocate pseudo-ttys, or expect interactive input.
- **Never Use RunPersistent Unless Explicitly Required**: Default to non-persistent command runs with short, bounded execution times to prevent background task demotion.
- **Fail Fast over Background Polling**: If a remote node or service does not respond within 3–5 seconds, fail immediately and report the error rather than waiting or scheduling recurring timer wakeups.

## Execution Speed & Tool Batching Invariants
- **Batch Independent Commands**: Always combine related inspection, diagnostics, and file reads into a single combined shell script or multi-tool call rather than making sequential round-trips.
- **Filter Locally with Predator Hardware**: Use Predator's native speed (`rg`, `head`, `tail`, `grep`, `jq`, `awk`) to filter command output locally BEFORE returning it to the agent context. Never dump large unpruned logs into the chat.
- **Preserve Context Budget**: Keep tool results compact and concise to maintain low token payload sizes, enabling maximum cloud streaming speed.


## Terminal Execution & Anti-Queue Invariants
- **FORBIDDEN: Named Persistent Terminal Queues**: NEVER specify `RequestedTerminalID` or `RunPersistent: true` unless the user explicitly orders a persistent session. Named terminals (e.g. `term_japan`, `term1`) lock execution behind internal pty queues, causing 2-5 minute execution delays.
- **Always Use Direct Non-Persistent Execution**: Run all commands in clean, non-persistent, unqueued shell invocations (`RunPersistent: false`, omit `RequestedTerminalID`).
- **Strict Command Timeouts**: Every network, remote SSH, or external command MUST be wrapped in a hard local timeout (e.g. `timeout 5s ssh -o ConnectTimeout=3 ...`).
- **Batch Independent Commands**: Always combine related inspection and command execution into a single combined shell script rather than making sequential round-trips.
- **Filter Locally with Predator Hardware**: Use Predator's native speed (`rg`, `head`, `tail`, `grep`, `jq`, `awk`) to filter command output locally BEFORE returning it to the agent context. Never dump large unpruned logs into the chat.

