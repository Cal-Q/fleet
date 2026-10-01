#!/usr/bin/env python3
"""Orchestration wrapper: pull down anything new, regenerate the decks, push the result back."""

from __future__ import annotations

import gc
import os
import sys
import time
from pathlib import Path

from anki_sync.sync_helpers import (
    anki_already_running,
    get_anki_base_and_profile,
)

ANKI_PYTHON = '/usr/local/share/anki/python/bin/python3'
ANKI_PACKAGES = '/usr/local/share/anki/app_packages'

# Transparent auto-delegation: If on Oracle VPS, dispatch to IONOS primary host
if not os.path.isfile(ANKI_PYTHON):
    import shutil
    import subprocess
    if shutil.which('ssh'):
        res = subprocess.run(['ssh', '-o', 'ConnectTimeout=8', 'ionos', 'python3 /opt/japan/core/sync_and_push.py'] + sys.argv[1:])
        sys.exit(res.returncode)
    else:
        sys.stderr.write("[sync_and_push] ERROR: Modern Anki runtime not found and SSH unavailable.\n")
        sys.exit(1)

if ANKI_PACKAGES not in sys.path:
    sys.path.insert(0, ANKI_PACKAGES)

if sys.executable != ANKI_PYTHON and os.path.isfile(ANKI_PYTHON):
    cur_pp = os.environ.get('PYTHONPATH', '')
    os.environ['PYTHONPATH'] = f'{ANKI_PACKAGES}:{cur_pp}'.strip(':')
    os.execv(ANKI_PYTHON, [ANKI_PYTHON] + sys.argv)


REPO_ROOT = Path(__file__).resolve().parent


def log(message: str) -> None:
    print(f"[sync_and_push] {message}", flush=True)


def run_pipeline() -> bool:
    log("Running anki_sync pipeline...")
    from anki_sync.main import main as pipeline_main
    return pipeline_main() == 0


def pre_sync_and_leech_lifecycle() -> bool:
    log("Pre-sync: pulling down changes from AnkiWeb and running leech lifecycle...")
    base_dir, profile_name = get_anki_base_and_profile(REPO_ROOT)
    col = None
    pm = None
    try:
        import aqt.profiles
        import anki.collection
        import anki.sync_pb2
        from anki_sync.leech_manager import process_leech_lifecycle

        pm = aqt.profiles.ProfileManager(base_dir)
        pm.setupMeta()
        pm.load(profile_name)
        auth = pm.sync_auth()
        if not auth:
            log("No sync auth found in profile, skipping remote pull.")
            return False

        col_path = pm.collectionPath()
        col = anki.collection.Collection(col_path)
        try:
            uncommitted = (
                col.db.scalar("SELECT count(*) FROM cards WHERE usn = -1")
                or col.db.scalar("SELECT count(*) FROM notes WHERE usn = -1")
            )
            if uncommitted:
                log("Local collection has uncommitted changes — skipping pre-sync pull to preserve local edits.")
                return True

            res = col.sync_collection(auth, sync_media=False)
            if getattr(res, "required", None) in (
                anki.sync_pb2.SyncCollectionResponse.FULL_SYNC,
                anki.sync_pb2.SyncCollectionResponse.FULL_DOWNLOAD,
            ):
                log("AnkiWeb requested FULL_DOWNLOAD — downloading collection...")
                col.close_for_full_sync()
                col.full_upload_or_download(auth=auth, server_usn=None, upload=False)
                col.reopen(after_full_sync=True)

            l_res = process_leech_lifecycle(col, cooldown_days=30)
            if l_res.dconf_updated > 0:
                log(f"Enforced leechAction=0 on {l_res.dconf_updated} deck configs.")
            if l_res.newly_suspended:
                log(f"Suspended {len(l_res.newly_suspended)} active leech cards.")
            if l_res.rehabilitated:
                log(f"Rehabilitated {len(l_res.rehabilitated)} suspended cards.")
            return True
        finally:
            if col:
                col.close()
            try:
                os.chmod(col_path, 0o664)
            except Exception:
                pass
    except Exception as e:
        log(f"Pre-sync encountered error: {e}")
        return False
    finally:
        del col
        del pm
        gc.collect()


def post_sync() -> bool:
    log("Post-sync: checking for local changes to push to AnkiWeb...")
    base_dir, profile_name = get_anki_base_and_profile(REPO_ROOT)
    col = None
    pm = None
    try:
        import aqt.profiles
        import anki.collection
        import anki.sync_pb2

        pm = aqt.profiles.ProfileManager(base_dir)
        pm.setupMeta()
        pm.load(profile_name)
        col_path = pm.collectionPath()
        col = anki.collection.Collection(col_path)
        try:
            uncommitted = any(
                col.db.scalar(f"SELECT 1 FROM {table} WHERE usn = -1 LIMIT 1")
                for table in ("cards", "notes", "graves", "decks", "deck_config", "config", "col")
            )
            if not uncommitted:
                log("No local changes to push — collection already up to date.")
                return True

            auth = pm.sync_auth()
            if not auth:
                log("No sync auth found in profile, skipping remote push.")
                return False

            res = col.sync_collection(auth, sync_media=False)
            required = getattr(res, "required", 0)
            if required != 0:
                log(f"WARNING: AnkiWeb sync indicated required={required}, skipping forced full upload to preserve delta sync.")
            else:
                log("Delta sync completed successfully.")
            return True
        finally:
            if col:
                col.close()
            try:
                os.chmod(col_path, 0o664)
            except Exception:
                pass
    except Exception as e:
        log(f"Post-sync encountered error: {e}")
        return False
    finally:
        del col
        del pm
        gc.collect()


sync_via_anki = post_sync


def check_and_run_daily_fsrs() -> None:
    try:
        from core.fsrs_daemon import run_daily_fsrs_recalibration, CARD_STATES_FILE
        import datetime
        if not os.path.exists(CARD_STATES_FILE) or datetime.date.fromtimestamp(os.path.getmtime(CARD_STATES_FILE)) != datetime.date.today():
            log("Running daily FSRS memory & weight recalibration...")
            run_daily_fsrs_recalibration(0.90, apply_to_anki=True)
    except Exception as e:
        log(f"FSRS recalibration notice: {e}")


def main() -> int:
    if anki_already_running():
        log("FAILED: Anki is running — refusing to write.")
        return 1
    if not pre_sync_and_leech_lifecycle():
        return 1
    check_and_run_daily_fsrs()
    if not run_pipeline():
        return 1
    if not post_sync():
        return 1
    log("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
