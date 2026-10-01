#!/usr/bin/env python3
"""
extract_and_prepare_tpu_data.py — Unified Anki Review Log Extractor & TPU Feature Pipeline

Aggregates all historical reviews across all 27 collection backups, snapshots,
and active databases, performs deduplication, builds cognitive fatigue features,
and exports directly to:
1. data/anki_reviews_consolidated.parquet (fast columnar format)
2. data/anki_reviews_tpu.npz (pre-engineered tensors ready for TPU HBM)
3. data/anki_reviews_summary.json (metadata and statistics)
"""

import os
import glob
import json
import math
import sqlite3
import subprocess
import tempfile
import zipfile
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime

WORKSPACE_DIR = "/mnt/workspaces/japan"
DATA_DIR = os.path.join(WORKSPACE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

CANDIDATE_PATHS = [
    glob.glob(f"{WORKSPACE_DIR}/.local/share/Anki2/User 1/backups/*"),
    glob.glob(f"{WORKSPACE_DIR}/.local/share/Anki2/User 1/collection.anki2*"),
    glob.glob(f"{WORKSPACE_DIR}/data/collection.anki2*"),
    glob.glob(f"{WORKSPACE_DIR}/data/snapshot_*.anki2*"),
    glob.glob(f"{WORKSPACE_DIR}/collection.anki2*"),
    glob.glob("/opt/japan/.local/share/Anki2/User 1/backups/*"),
    glob.glob("/opt/japan/.local/share/Anki2/User 1/collection.anki2*"),
]

def get_sqlite_conn(file_path: str, tmpdir: str):
    """Returns a sqlite3 connection, handling .colpkg (zstd/zip) or raw .anki2."""
    if file_path.endswith(".colpkg"):
        with zipfile.ZipFile(file_path) as z:
            names = z.namelist()
            if "collection.anki21b" in names:
                data = z.read("collection.anki21b")
                p = subprocess.Popen(
                    ["zstd", "-d"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                decompressed, err = p.communicate(input=data)
                if p.returncode != 0:
                    raise RuntimeError(f"zstd failed on {file_path}: {err.decode('utf-8', errors='replace')}")
                tmp_db = os.path.join(tmpdir, f"temp_{os.path.basename(file_path)}.anki2")
                with open(tmp_db, "wb") as f:
                    f.write(decompressed)
                return sqlite3.connect(tmp_db), tmp_db
            elif "collection.anki2" in names:
                tmp_db = os.path.join(tmpdir, f"temp_{os.path.basename(file_path)}.anki2")
                with open(tmp_db, "wb") as f:
                    f.write(z.read("collection.anki2"))
                return sqlite3.connect(tmp_db), tmp_db
            else:
                raise ValueError(f"No collection database found in {file_path}")
    else:
        return sqlite3.connect(file_path), None

def extract_all_reviews():
    all_files = []
    for group in CANDIDATE_PATHS:
        for f in group:
            if os.path.isfile(f) and not f.endswith(".log") and not f.endswith(".txt") and not f.endswith(".db2"):
                all_files.append(os.path.realpath(f))
    
    unique_files = sorted(list(set(all_files)))
    print(f"[*] Found {len(unique_files)} unique collection/backup files to scan.")

    # Dictionary mapping review id -> (cid, usn, ease, ivl, lastIvl, factor, time, type)
    reviews_dict = {}

    with tempfile.TemporaryDirectory() as tmpdir:
        for idx, fpath in enumerate(unique_files, 1):
            fname = os.path.basename(fpath)
            tmp_db = None
            try:
                conn, tmp_db = get_sqlite_conn(fpath, tmpdir)
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='revlog'")
                if cur.fetchone():
                    cur.execute("SELECT id, cid, usn, ease, ivl, lastIvl, factor, time, type FROM revlog")
                    rows = cur.fetchall()
                    new_count = 0
                    for row in rows:
                        rid = row[0]
                        if rid not in reviews_dict:
                            reviews_dict[rid] = row
                            new_count += 1
                    print(f"[{idx}/{len(unique_files)}] {fname}: {len(rows):,} reviews ({new_count:,} new)")
                conn.close()
            except Exception as e:
                print(f"[{idx}/{len(unique_files)}] {fname}: Skipped ({e})")
            finally:
                if tmp_db and os.path.exists(tmp_db):
                    os.remove(tmp_db)

    print(f"\n[+] Total unique review records extracted: {len(reviews_dict):,}")
    return list(reviews_dict.values())

def build_features(raw_reviews):
    """
    Sorts reviews chronologically and computes session dynamics,
    rolling cognitive fatigue indicators, and pause recovery metrics.
    """
    print("[*] Sorting reviews chronologically...")
    # row: (id, cid, usn, ease, ivl, lastIvl, factor, time, type)
    # id is timestamp in milliseconds
    sorted_reviews = sorted(raw_reviews, key=lambda r: r[0])
    N = len(sorted_reviews)

    print(f"[*] Engineering features for {N:,} reviews...")

    # Session threshold: 15 minutes (900 seconds) of inactivity
    SESSION_GAP_MS = 15 * 60 * 1000

    # Arrays for engineered data
    rev_id = np.empty(N, dtype=np.int64)
    card_id = np.empty(N, dtype=np.int64)
    ease = np.empty(N, dtype=np.int8)
    ivl = np.empty(N, dtype=np.int32)
    last_ivl = np.empty(N, dtype=np.int32)
    factor = np.empty(N, dtype=np.int32)
    time_ms = np.empty(N, dtype=np.int32)
    rev_type = np.empty(N, dtype=np.int8)

    session_id = np.empty(N, dtype=np.int32)
    session_card_idx = np.empty(N, dtype=np.int32)
    session_elapsed_sec = np.empty(N, dtype=np.float32)
    inter_review_gap_sec = np.empty(N, dtype=np.float32)

    circadian_hour = np.empty(N, dtype=np.float32)
    circadian_sin = np.empty(N, dtype=np.float32)
    circadian_cos = np.empty(N, dtype=np.float32)

    log_latency = np.empty(N, dtype=np.float32)
    is_lapse = np.empty(N, dtype=np.float32)
    is_hard = np.empty(N, dtype=np.float32)

    curr_session = 0
    curr_card_idx = 0
    curr_session_start_ms = sorted_reviews[0][0]
    last_ts = sorted_reviews[0][0]

    for i, row in enumerate(sorted_reviews):
        ts = row[0]
        cid = row[1]
        e = row[3]
        iv = row[4]
        liv = row[5]
        fac = row[6]
        t = max(row[7], 100) # clip minimum to 100ms
        rtype = row[8]

        gap_ms = ts - last_ts
        if i == 0 or gap_ms > SESSION_GAP_MS:
            curr_session += 1
            curr_card_idx = 1
            curr_session_start_ms = ts
            gap_sec = 0.0
        else:
            curr_card_idx += 1
            gap_sec = gap_ms / 1000.0

        rev_id[i] = ts
        card_id[i] = cid
        ease[i] = e
        ivl[i] = iv
        last_ivl[i] = liv
        factor[i] = fac
        time_ms[i] = t
        rev_type[i] = rtype

        session_id[i] = curr_session
        session_card_idx[i] = curr_card_idx
        session_elapsed_sec[i] = (ts - curr_session_start_ms) / 1000.0
        inter_review_gap_sec[i] = gap_sec

        dt = datetime.fromtimestamp(ts / 1000.0)
        hour_val = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
        circadian_hour[i] = hour_val
        circadian_sin[i] = math.sin(2.0 * math.pi * hour_val / 24.0)
        circadian_cos[i] = math.cos(2.0 * math.pi * hour_val / 24.0)

        log_lat = math.log(float(t))
        log_latency[i] = log_lat
        is_lapse[i] = 1.0 if e == 1 else 0.0
        is_hard[i] = 1.0 if e == 2 else 0.0

        last_ts = ts

    # Rolling statistics within session
    rolling_lat_mean_10 = np.empty(N, dtype=np.float32)
    rolling_lat_std_10 = np.empty(N, dtype=np.float32)
    rolling_lapse_rate_10 = np.empty(N, dtype=np.float32)

    rolling_lat_mean_30 = np.empty(N, dtype=np.float32)
    rolling_lapse_rate_30 = np.empty(N, dtype=np.float32)

    # Future targets: lapse rate in the upcoming 5 and 10 cards
    target_next_5_lapse_rate = np.empty(N, dtype=np.float32)
    target_next_10_lapse_rate = np.empty(N, dtype=np.float32)

    print("[*] Computing rolling fatigue windows and future targets...")
    for i in range(N):
        s_id = session_id[i]
        
        # 10-window back
        start_10 = max(0, i - 9)
        while start_10 < i and session_id[start_10] != s_id:
            start_10 += 1
        w10_lat = log_latency[start_10 : i + 1]
        w10_lapse = is_lapse[start_10 : i + 1]
        rolling_lat_mean_10[i] = float(np.mean(w10_lat))
        rolling_lat_std_10[i] = float(np.std(w10_lat)) if len(w10_lat) > 1 else 0.0
        rolling_lapse_rate_10[i] = float(np.mean(w10_lapse))

        # 30-window back
        start_30 = max(0, i - 29)
        while start_30 < i and session_id[start_30] != s_id:
            start_30 += 1
        w30_lat = log_latency[start_30 : i + 1]
        w30_lapse = is_lapse[start_30 : i + 1]
        rolling_lat_mean_30[i] = float(np.mean(w30_lat))
        rolling_lapse_rate_30[i] = float(np.mean(w30_lapse))

        # Future targets (within same session)
        end_5 = min(N, i + 6)
        future_5 = [is_lapse[k] for k in range(i + 1, end_5) if session_id[k] == s_id]
        target_next_5_lapse_rate[i] = float(np.mean(future_5)) if future_5 else rolling_lapse_rate_10[i]

        end_10 = min(N, i + 11)
        future_10 = [is_lapse[k] for k in range(i + 1, end_10) if session_id[k] == s_id]
        target_next_10_lapse_rate[i] = float(np.mean(future_10)) if future_10 else rolling_lapse_rate_10[i]

    # Latency drift: current 10-window latency relative to 30-window baseline
    latency_drift = rolling_lat_mean_10 - rolling_lat_mean_30

    data_dict = {
        "rev_id": rev_id,
        "card_id": card_id,
        "ease": ease,
        "ivl": ivl,
        "last_ivl": last_ivl,
        "factor": factor,
        "time_ms": time_ms,
        "rev_type": rev_type,
        "session_id": session_id,
        "session_card_idx": session_card_idx,
        "session_elapsed_sec": session_elapsed_sec,
        "inter_review_gap_sec": inter_review_gap_sec,
        "circadian_hour": circadian_hour,
        "circadian_sin": circadian_sin,
        "circadian_cos": circadian_cos,
        "log_latency": log_latency,
        "is_lapse": is_lapse,
        "is_hard": is_hard,
        "rolling_lat_mean_10": rolling_lat_mean_10,
        "rolling_lat_std_10": rolling_lat_std_10,
        "rolling_lapse_rate_10": rolling_lapse_rate_10,
        "rolling_lat_mean_30": rolling_lat_mean_30,
        "rolling_lapse_rate_30": rolling_lapse_rate_30,
        "latency_drift": latency_drift,
        "target_next_5_lapse_rate": target_next_5_lapse_rate,
        "target_next_10_lapse_rate": target_next_10_lapse_rate,
    }

    return data_dict, curr_session

def export_all(data_dict, total_sessions):
    # 1. Export Parquet
    parquet_path = os.path.join(DATA_DIR, "anki_reviews_consolidated.parquet")
    print(f"[*] Exporting to Parquet: {parquet_path}...")
    table = pa.Table.from_pydict(data_dict)
    pq.write_table(table, parquet_path, compression="zstd")
    parquet_size_mb = os.path.getsize(parquet_path) / (1024 * 1024)
    print(f"[+] Parquet exported: {parquet_size_mb:.2f} MB")

    # 2. Export TPU .npz
    npz_path = os.path.join(DATA_DIR, "anki_reviews_tpu.npz")
    print(f"[*] Exporting to TPU-ready NumPy archive: {npz_path}...")

    # Feature matrix suitable for direct tensor input into TPU (float32)
    feature_cols = [
        "log_latency",
        "rolling_lat_mean_10",
        "rolling_lat_std_10",
        "rolling_lapse_rate_10",
        "rolling_lat_mean_30",
        "rolling_lapse_rate_30",
        "latency_drift",
        "session_card_idx",
        "session_elapsed_sec",
        "inter_review_gap_sec",
        "circadian_sin",
        "circadian_cos",
        "ivl",
        "last_ivl",
        "factor",
        "rev_type",
    ]
    
    X = np.column_stack([data_dict[col].astype(np.float32) for col in feature_cols])
    y_next5 = data_dict["target_next_5_lapse_rate"].astype(np.float32)
    y_next10 = data_dict["target_next_10_lapse_rate"].astype(np.float32)
    y_current_ease = data_dict["ease"].astype(np.int32)
    session_ids = data_dict["session_id"].astype(np.int32)
    timestamps = data_dict["rev_id"].astype(np.int64)

    np.savez_compressed(
        npz_path,
        X=X,
        y_next5=y_next5,
        y_next10=y_next10,
        y_current_ease=y_current_ease,
        session_ids=session_ids,
        timestamps=timestamps,
        feature_names=np.array(feature_cols),
    )
    npz_size_mb = os.path.getsize(npz_path) / (1024 * 1024)
    print(f"[+] TPU .npz exported: {npz_size_mb:.2f} MB")

    # 3. Export Summary JSON
    summary_path = os.path.join(DATA_DIR, "anki_reviews_summary.json")
    first_date = datetime.fromtimestamp(data_dict["rev_id"][0] / 1000.0).isoformat()
    last_date = datetime.fromtimestamp(data_dict["rev_id"][-1] / 1000.0).isoformat()
    
    summary = {
        "total_reviews": len(data_dict["rev_id"]),
        "total_sessions": int(total_sessions),
        "date_range": {
            "start": first_date,
            "end": last_date,
        },
        "overall_lapse_rate": float(np.mean(data_dict["is_lapse"])),
        "mean_latency_ms": float(np.mean(data_dict["time_ms"])),
        "median_latency_ms": float(np.median(data_dict["time_ms"])),
        "features": feature_cols,
        "files": {
            "parquet": parquet_path,
            "parquet_size_mb": round(parquet_size_mb, 2),
            "npz": npz_path,
            "npz_size_mb": round(npz_size_mb, 2),
        }
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"[+] Summary saved to {summary_path}")
    print(json.dumps(summary, indent=2))

def main():
    raw_reviews = extract_all_reviews()
    data_dict, total_sessions = build_features(raw_reviews)
    export_all(data_dict, total_sessions)

if __name__ == "__main__":
    main()
