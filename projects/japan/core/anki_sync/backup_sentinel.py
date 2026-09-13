# core/anki_sync/backup_sentinel.py — SQLite Snapshot Backup & Integrity Sentinel
import glob
import os
import sqlite3
import time
from typing import Any, Dict


def get_backup_dir(col_path: str) -> str:
    parent = os.path.dirname(os.path.abspath(col_path))
    bdir = os.path.join(parent, "backups")
    os.makedirs(bdir, exist_ok=True)
    return bdir


def create_snapshot(col_path: str, max_snapshots: int = 7) -> str:
    """Create a fast atomic SQLite backup of the collection and rotate old snapshots."""
    if not os.path.isfile(col_path):
        return ""

    bdir = get_backup_dir(col_path)
    now_ts = int(time.time())
    dest_path = os.path.join(bdir, f"snapshot_{now_ts}.anki2")

    src = sqlite3.connect(f"file:{col_path}?mode=ro", uri=True)
    dst = sqlite3.connect(dest_path)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()

    try:
        os.chmod(dest_path, 0o664)
    except Exception:
        pass

    # Rotate old snapshot files
    existing = sorted(glob.glob(os.path.join(bdir, "snapshot_*.anki2")))
    if len(existing) > max_snapshots:
        for old_file in existing[:-max_snapshots]:
            try:
                os.remove(old_file)
            except Exception:
                pass

    return dest_path


def verify_collection_integrity(col_path: str) -> Dict[str, Any]:
    """Execute SQLite integrity check and schema invariant probes."""
    if not os.path.isfile(col_path):
        return {"healthy": False, "error": "File not found"}

    conn = sqlite3.connect(f"file:{col_path}?mode=ro", uri=True)
    try:
        conn.create_collation(
            "unicase",
            lambda a, b: (a.casefold() > b.casefold()) - (a.casefold() < b.casefold())
        )
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check(1)")
        row = cursor.fetchone()
        pragma_ok = row and row[0] == "ok"

        cursor.execute("SELECT count(*) FROM cards WHERE nid NOT IN (SELECT id FROM notes)")
        orphan_cards = cursor.fetchone()[0]

        cursor.execute("SELECT count(*) FROM cards WHERE usn = -1")
        uncommitted_cards = cursor.fetchone()[0]

        cursor.execute("SELECT count(*) FROM notes WHERE usn = -1")
        uncommitted_notes = cursor.fetchone()[0]

        cursor.execute("SELECT max(id) FROM revlog")
        latest_revlog = cursor.fetchone()[0] or 0

        cursor.execute("SELECT count(*) FROM cards")
        total_cards = cursor.fetchone()[0]

        healthy = pragma_ok and (orphan_cards == 0)

        return {
            "healthy": healthy,
            "pragma_integrity": "ok" if pragma_ok else str(row),
            "orphan_cards": orphan_cards,
            "uncommitted_cards": uncommitted_cards,
            "uncommitted_notes": uncommitted_notes,
            "latest_revlog_id": latest_revlog,
            "total_cards": total_cards,
        }
    finally:
        conn.close()
