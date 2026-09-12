"""Storage manager for Renpho measurements."""

import json
import sqlite3
from pathlib import Path

DATA_DIR = Path("/opt/master/data/renpho")
JSONL_PATH = DATA_DIR / "measurements.jsonl"
DB_PATH = DATA_DIR / "measurements.db"


def init_db():
    """Ensure database schema exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                timestamp INTEGER,
                local_time TEXT,
                weight_kg REAL,
                bmi REAL,
                bodyfat_pct REAL,
                subfat_pct REAL,
                visfat INTEGER,
                sinew_kg REAL,
                muscle_pct REAL,
                smm_kg REAL,
                bone_kg REAL,
                water_pct REAL,
                protein_pct REAL,
                bmr_kcal INTEGER,
                body_age INTEGER,
                raw_json TEXT
            )
        """)
        conn.commit()


def save_measurements(records: list[dict]) -> int:
    """Save records to SQLite and JSONL with deduplication."""
    init_db()
    new_count = 0
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        for r in records:
            mid = r.get("id")
            if not mid:
                continue
            cursor.execute("SELECT 1 FROM measurements WHERE id = ?", (mid,))
            if cursor.fetchone():
                continue
            cursor.execute("""
                INSERT INTO measurements (
                    id, user_id, timestamp, local_time, weight_kg, bmi, bodyfat_pct,
                    subfat_pct, visfat, sinew_kg, muscle_pct, smm_kg, bone_kg,
                    water_pct, protein_pct, bmr_kcal, body_age, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                mid,
                r.get("userId"),
                r.get("timeStamp"),
                r.get("localCreatedAt"),
                r.get("weight"),
                r.get("bmi"),
                r.get("bodyfat"),
                r.get("subfat"),
                r.get("visfat"),
                r.get("sinew"),
                r.get("muscle"),
                r.get("smmMass"),
                r.get("bone"),
                r.get("water"),
                r.get("protein"),
                r.get("bmr"),
                r.get("bodyage"),
                json.dumps(r),
            ))
            new_count += 1
            with open(JSONL_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(r) + "\n")
        conn.commit()
    return new_count


def get_latest_measurement() -> dict | None:
    """Fetch the newest measurement record."""
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM measurements ORDER BY timestamp DESC LIMIT 1")
        row = cur.fetchone()
        return dict(row) if row else None


def get_all_records(limit: int = 50) -> list[dict]:
    """Fetch recent measurements ordered newest first."""
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM measurements ORDER BY timestamp DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]
