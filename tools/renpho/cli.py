"""CLI for Renpho Cloud sync and inspection."""

import sys
import argparse
from datetime import datetime
from .client import RenphoClient
from .storage import save_measurements, get_latest_measurement, get_all_records
from .constants import METRICS_DISPLAY


def sync_command():
    """Sync scale records from Renpho Cloud."""
    print("⚡ Connecting to Renpho Cloud API...")
    try:
        client = RenphoClient()
        client.login()
        records = client.get_all_measurements()
        new_count = save_measurements(records)
        print(f"✅ Sync complete! Fetched {len(records)} total records ({new_count} new).")
        show_latest()
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        sys.exit(1)


def show_latest():
    """Display latest scale record in formatted table."""
    row = get_latest_measurement()
    if not row:
        print("No measurements recorded yet.")
        return
    ts = row.get("timestamp", 0)
    dt_str = row.get("local_time") or datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "=" * 50)
    print(f"       RENPHO METRICS - {dt_str}")
    print("=" * 50)
    for key, label, unit in METRICS_DISPLAY:
        val = row.get(f"{key}_kg") or row.get(f"{key}_pct") or row.get(key)
        if val is None:
            val = row.get(key)
        if val is not None:
            val_str = f"{val:.1f}" if isinstance(val, float) else f"{val}"
            print(f"  {label:<22} : {val_str:>7} {unit}")
    print("=" * 50 + "\n")


def show_history():
    """Display historical measurements table."""
    records = get_all_records(limit=20)
    if not records:
        print("No measurement history available.")
        return
    print("\n" + "=" * 70)
    print(f"{'DATE & TIME':<18} | {'WEIGHT':<8} | {'FAT %':<7} | {'MUSCLE %':<9} | {'BMI':<5} | {'BMR':<5}")
    print("-" * 70)
    for r in records:
        ts = r.get("timestamp", 0)
        dt_str = (r.get("local_time") or datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M"))[:16]
        w = f"{r.get('weight_kg', 0):.1f} kg"
        fat = f"{r.get('bodyfat_pct', 0):.1f}%"
        mus = f"{r.get('muscle_pct', 0):.1f}%"
        bmi = f"{r.get('bmi', 0):.1f}"
        bmr = f"{r.get('bmr_kcal', 0)}"
        print(f"{dt_str:<18} | {w:<8} | {fat:<7} | {mus:<9} | {bmi:<5} | {bmr:<5}")
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Renpho Scale Cloud CLI")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("sync", help="Sync latest data from Renpho Cloud")
    sub.add_parser("latest", help="Show latest body composition")
    sub.add_parser("history", help="Show measurement history")

    args = parser.parse_args()
    if args.cmd == "sync":
        sync_command()
    elif args.cmd == "history":
        show_history()
    else:
        show_latest()


if __name__ == "__main__":
    main()
