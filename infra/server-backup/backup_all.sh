#!/usr/bin/env bash
# ==============================================================================
# Comprehensive Server Backup, Git Sync & Cold Storage Pipeline
# Schedule: Hourly Automated Run
# ==============================================================================
set -euo pipefail
umask 077

TIMESTAMP=$(date -u +%Y%m%d_%H%M%SZ)
STAGING_DIR="/opt/server-backup/staging/${TIMESTAMP}"
LOG_FILE="/var/log/server-backup/backup_${TIMESTAMP}.log"
CONFIG_PATH="/etc/rclone/rclone.conf"
REMOTE_TARGET="gdrive_backup:server-backups"
LOCK_FILE="/tmp/server_backup.lock"
RETENTION_DAYS=7

# Concurrency lock
exec 8>"${LOCK_FILE}"
if ! flock -n 8; then
    echo "[$(date -Is)] Backup already running. Exiting."
    exit 0
fi

mkdir -p "${STAGING_DIR}" "$(dirname "${LOG_FILE}")"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "========================================================"
echo "Starting Hourly Backup & Git Sync: ${TIMESTAMP}"
echo "========================================================"

# --- 1. AUTOMATED GIT SYNC & PUSH (ALL REPOS) ---
echo "[1/5] Running automated Git commit & push across all repositories..."
/opt/server-backup/auto_git_sync.sh || true

# --- 2. ATOMIC DATABASE BACKUPS (100% OF SERVER DBS) ---
echo "[2/5] Performing atomic database backups across all services..."
mkdir -p "${STAGING_DIR}/databases"

declare -A DBS=(
    ["smash_segment_index"]="/home/smashbot/smash-storage/segment_index.db"
    ["smash_zen_recordings"]="/home/smashbot/smash-agent/backend/zen_recordings.db"
    ["pokevault_codes"]="/opt/pokevault/pokemon_codes.db"
    ["pokevault_vault"]="/var/lib/pokevault/vault.db"
    ["pokevault_cards"]="/var/lib/pokevault/cards.db"
    ["pokevault_wishlists"]="/var/lib/pokevault/wishlists.db"
    ["bunpro_anki"]="/opt/bunpro-anki/bunpro.db"
    ["japan_dict_index"]="/opt/japan/data/dict_index.sqlite3"
    ["japan_anki_collection"]="/opt/japan/.local/share/Anki2/User 1/collection.anki2"
    ["cardmarket_scraper"]="/root/cardmarket-vps-api/scraper_database.db"
    ["pokemon_versions"]="/root/pokemon-space-files/backend/card-versions/versions.db"
    ["filebrowser"]="/opt/filebrowser.db"
    ["redis_dump"]="/var/lib/redis/dump.rdb"
)

for NAME in "${!DBS[@]}"; do
    DB_PATH="${DBS[$NAME]}"
    if [ -f "${DB_PATH}" ]; then
        MAGIC=$(head -c 16 "${DB_PATH}" 2>/dev/null || true)
        if [[ "${MAGIC}" == *"SQLite format 3"* ]]; then
            echo "  - Backing up SQLite DB: ${NAME} (${DB_PATH})..."
            sqlite3 "${DB_PATH}" ".backup '${STAGING_DIR}/databases/${NAME}.db'"
        else
            echo "  - Copying raw DB / Store: ${NAME} (${DB_PATH})..."
            cp -p "${DB_PATH}" "${STAGING_DIR}/databases/${NAME}.db"
        fi
    fi
done

# --- 3. SYSTEM CONFIGURATIONS & CRONTABS ---
echo "[3/5] Archiving system configurations & crontabs..."
mkdir -p "${STAGING_DIR}/configs/crontabs"
tar -czf "${STAGING_DIR}/configs/etc_nginx.tar.gz" -C /etc nginx 2>/dev/null || true
tar -czf "${STAGING_DIR}/configs/etc_systemd.tar.gz" -C /etc/systemd system 2>/dev/null || true
tar -czf "${STAGING_DIR}/configs/etc_ssh.tar.gz" -C /etc ssh 2>/dev/null || true

for u in $(cut -f1 -d: /etc/passwd); do
    crontab -u "$u" -l > "${STAGING_DIR}/configs/crontabs/${u}.cron" 2>/dev/null || true
    [ ! -s "${STAGING_DIR}/configs/crontabs/${u}.cron" ] && rm -f "${STAGING_DIR}/configs/crontabs/${u}.cron"
done

# --- 4. CREATE ZSTD COMPRESSED HOURLY BUNDLE ---
echo "[4/5] Packaging system & database bundle with Zstandard (zstd)..."
BUNDLE_PATH="/opt/server-backup/backup_${TIMESTAMP}.tar.zst"
tar -cf - -C "/opt/server-backup/staging" "${TIMESTAMP}" | zstd -3 -T0 -o "${BUNDLE_PATH}"

# Remove raw staging folder
rm -rf "${STAGING_DIR}"

# Upload hourly compressed bundle
echo "  - Uploading bundle to Google Drive (${REMOTE_TARGET}/daily/)..."
rclone copy "${BUNDLE_PATH}" "${REMOTE_TARGET}/daily/"     --config "${CONFIG_PATH}"     --checksum     --retries 3     --low-level-retries 10     --stats 5s

# --- 5. COLD STORAGE MEDIA & ASSET SYNC (IMAGES / VODS / LOGS) ---
# Japan Hard Assets (Exams, Applications, Fonts)
rclone copy "/opt/japan/exams/" "${REMOTE_TARGET}/assets/japan/exams/" --include "*.pdf" --config "${CONFIG_PATH}" || true
rclone copy "/opt/japan/applications/" "${REMOTE_TARGET}/assets/japan/applications/" --include "*.pdf" --config "${CONFIG_PATH}" || true

echo "[5/5] Syncing cold-storable media, images, and archives..."

# SSBU Character & Stage Gallery Icons
if [ -d "/home/ssbu_brain/gallery" ]; then
    rclone sync "/home/ssbu_brain/gallery" "${REMOTE_TARGET}/media/ssbu-gallery/"         --config "${CONFIG_PATH}" --checksum --transfers 4 || true
fi

# SSBU Mod & Layout Binary Backups
if [ -d "/home/ssbu_brain/backups" ]; then
    rclone sync "/home/ssbu_brain/backups" "${REMOTE_TARGET}/media/ssbu-mod-backups/"         --config "${CONFIG_PATH}" --checksum --transfers 4 || true
fi

# PokeVault Scanned & Catalog Images
if [ -d "/opt/pokevault/images" ]; then
    rclone sync "/opt/pokevault/images" "${REMOTE_TARGET}/media/pokevault-images/"         --config "${CONFIG_PATH}" --checksum --transfers 4 || true
fi

# Cardmarket Scraper Images
if [ -d "/root/cardmarket-vps-api/public/images" ]; then
    rclone sync "/root/cardmarket-vps-api/public/images" "${REMOTE_TARGET}/media/cardmarket-images/"         --config "${CONFIG_PATH}" --checksum --transfers 4 || true
fi

# Stale Telemetry Logs (>3 days old moved to cold storage)
if [ -d "/home/smashbot/smash-storage/telemetry/daily" ]; then
    rclone move "/home/smashbot/smash-storage/telemetry/daily" "${REMOTE_TARGET}/smash-telemetry-cold/"         --config "${CONFIG_PATH}"         --min-age 3d         --include "*.raw.log"         --transfers 4         --checksum || true
fi

# Prune local backups older than RETENTION_DAYS
find /opt/server-backup -name "backup_*.tar.zst" -mtime +"${RETENTION_DAYS}" -delete
find /var/log/server-backup -name "backup_*.log" -mtime +"${RETENTION_DAYS}" -delete

echo "========================================================"
echo "Hourly Backup & Git Sync Completed: $(date -u +"%Y-%m-%d %H:%M:%SZ")"
echo "Bundle: ${BUNDLE_PATH} ($(du -h "${BUNDLE_PATH}" | cut -f1))"
echo "========================================================"
