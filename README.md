# 👑 Cal-Q Fleet // Sovereign Server Infrastructure & Projects

Authoritative unified monorepo for Server 1 (IONOS) and Oracle Cloud VPS.

## 🛡️ Architecture & Invariants
- **Code (Git):** Strictly modular source code, HTML/CSS/JS, schemas, and configurations (<= 200 lines per file).
- **Hard Assets (Google Drive):** Binaries, fonts, media, and PDFs stored and served via \`/mnt/gdrive_cold\` (\`gdrive_backup:server-backups/assets/\`).
- **Databases (NVMe + Hourly Backups):** High-speed operational storage on local NVMe, backed up atomically hourly to Google Drive.
- **Hourly Loop:** Automated periodic commit & push to \`Cal-Q/fleet\` on GitHub via \`/opt/server-backup/auto_git_sync.sh\`.

## 📁 Repository Structure
- \`projects/\`: Service codebases (\`japan\`, \`pokevault\`, \`fitness\`, \`ssbu\`, etc.)
- \`infra/\`: Nginx site definitions, systemd service units, and backup scripts.
- \`tools/\`: Fleet management tools, daemons, and lifecycle scripts.
