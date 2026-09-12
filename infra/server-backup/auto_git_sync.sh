#!/usr/bin/env bash
# ==============================================================================
# Automated Multi-Repository Git Commit & Push Pipeline
# ==============================================================================
set -uo pipefail

echo "========================================================"
echo "Starting Automated Git Sync: $(date -u +"%Y-%m-%d %H:%M:%SZ")"
echo "========================================================"

# Update /etc/server-infra snapshots before checking git
mkdir -p /etc/server-infra/nginx-sites /etc/server-infra/systemd-units /etc/server-infra/ssh-configs
cp -r /etc/nginx/sites-available/* /etc/server-infra/nginx-sites/ 2>/dev/null || true
cp -r /etc/nginx/conf.d/* /etc/server-infra/nginx-sites/ 2>/dev/null || true
cp /etc/systemd/system/smash*.service /etc/server-infra/systemd-units/ 2>/dev/null || true
cp /etc/systemd/system/pokevault*.service /etc/server-infra/systemd-units/ 2>/dev/null || true
cp /etc/systemd/system/remote-print.service /etc/server-infra/systemd-units/ 2>/dev/null || true
cp /etc/systemd/system/anki-sync.* /etc/server-infra/systemd-units/ 2>/dev/null || true
cp /etc/systemd/system/server-backup.* /etc/server-infra/systemd-units/ 2>/dev/null || true
cp /etc/systemd/system/rclone-mount.service /etc/server-infra/systemd-units/ 2>/dev/null || true
cp /opt/server-backup/*.sh /etc/server-infra/systemd-units/ 2>/dev/null || true

declare -A REPOS=(
    ["smash-agent"]="/home/smashbot/smash-agent:smashbot"
    ["pokevault-backend"]="/opt/pokevault:pokeuser"
    ["pokevault-frontend"]="/var/www/pokevault:root"
    ["sinoira-gang"]="/home/SinoiaGang/sinoira-gang:SinoiaGang"
    ["remote-print"]="/opt/remote-print:printbot"
    ["japan-exam-tutor"]="/home/tutor/japan_exam_tutor:tutor"
    ["bunpro-anki"]="/opt/bunpro-anki:bunkibot"
    ["japan"]="/opt/japan:japan"
    ["cloudprint"]="/opt/cloudprint:root"
    ["server-infra"]="/etc/server-infra:root"
)

for NAME in "${!REPOS[@]}"; do
    ENTRY="${REPOS[$NAME]}"
    REPO_DIR="${ENTRY%%:*}"
    USER_RUN="${ENTRY##*:}"

    if [ -d "${REPO_DIR}/.git" ]; then
        # Check for uncommitted changes
        CHANGES=$(sudo -u "${USER_RUN}" git -C "${REPO_DIR}" status --porcelain 2>/dev/null | wc -l)
        BRANCH=$(sudo -u "${USER_RUN}" git -C "${REPO_DIR}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")

        if [ "${CHANGES}" -gt 0 ]; then
            echo "[GIT] ${NAME} (${REPO_DIR}): ${CHANGES} changes detected. Committing and pushing..."
            sudo -u "${USER_RUN}" git -C "${REPO_DIR}" add .
            sudo -u "${USER_RUN}" git -C "${REPO_DIR}" commit -m "chore(auto): Hourly automated git backup $(date -u +"%Y-%m-%d %H:%M:%SZ")" || true
            sudo -u "${USER_RUN}" git -C "${REPO_DIR}" push origin "${BRANCH}" || echo "  [WARN] Failed to push ${NAME}"
        else
            echo "[GIT] ${NAME}: Clean (no uncommitted changes)."
        fi
    fi
done

echo "Automated Git Sync Finished: $(date -u +"%Y-%m-%d %H:%M:%SZ")"
