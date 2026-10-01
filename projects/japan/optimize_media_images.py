#!/usr/bin/env python3
"""
core/optimize_media_images.py — Anki Collection Media Image Resizer & Optimizer
Resizes kanji diagram PNGs to fit actual app display dimensions (480x240 max)
with high-quality Lanczos resampling and adaptive palette compression.
Strictly <= 200 lines invariant.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Tuple
from PIL import Image

DEFAULT_MEDIA_DIR = "/opt/japan/.local/share/Anki2/User 1/collection.media"
MAX_WIDTH = 480
MAX_HEIGHT = 240


def optimize_single_image(
    file_path: str, max_w: int = MAX_WIDTH, max_h: int = MAX_HEIGHT
) -> Tuple[bool, int, int]:
    """Resizes a single image if it exceeds max bounds. Returns (changed, orig_size, new_size)."""
    try:
        orig_size = os.path.getsize(file_path)
        with Image.open(file_path) as im:
            orig_w, orig_h = im.size
            if orig_w <= max_w and orig_h <= max_h and orig_size < 35000:
                return False, orig_size, orig_size

            im_thumb = im.copy()
            if orig_w > max_w or orig_h > max_h:
                im_thumb.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)

            # Palette quantization for crisp diagrams and small footprint
            if im_thumb.mode in ("RGBA", "LA") or (im_thumb.mode == "P" and "transparency" in im_thumb.info):
                im_opt = im_thumb.convert("P", palette=Image.Palette.ADAPTIVE, colors=128)
            else:
                im_opt = im_thumb.convert("RGB").convert("P", palette=Image.Palette.ADAPTIVE, colors=128)

            tmp_path = file_path + ".opt_tmp"
            im_opt.save(tmp_path, "PNG", optimize=True)

            new_size = os.path.getsize(tmp_path)
            if new_size < orig_size or (orig_w > max_w or orig_h > max_h):
                os.replace(tmp_path, file_path)
                return True, orig_size, new_size
            else:
                if os.path.isfile(tmp_path):
                    os.remove(tmp_path)
                return False, orig_size, orig_size
    except Exception as e:
        print(f"Error optimizing {os.path.basename(file_path)}: {e}", file=sys.stderr)
        return False, 0, 0


from concurrent.futures import ThreadPoolExecutor, as_completed

def optimize_all_media_images(
    media_dir: str = DEFAULT_MEDIA_DIR, max_w: int = MAX_WIDTH, max_h: int = MAX_HEIGHT, max_workers: int = 8
) -> dict:
    """Batch optimizes all PNG files in media_dir concurrently."""
    if not os.path.isdir(media_dir):
        print(f"Media directory not found: {media_dir}", file=sys.stderr)
        return {"status": "error", "message": "Directory not found"}

    png_files = [f for f in os.listdir(media_dir) if f.lower().endswith(".png")]
    total_files = len(png_files)
    print(f"[*] Starting concurrent image optimization ({max_workers} workers) across {total_files} PNG images in {media_dir}...")
    t0 = time.time()

    total_orig = 0
    total_new = 0
    resized_count = 0
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(optimize_single_image, os.path.join(media_dir, f), max_w, max_h): f for f in png_files}
        for fut in as_completed(futures):
            changed, orig_sz, new_sz = fut.result()
            total_orig += orig_sz
            total_new += new_sz
            if changed:
                resized_count += 1
            completed += 1
            if completed % 500 == 0 or completed == total_files:
                elapsed = time.time() - t0
                print(f"    [{completed}/{total_files}] Processed ({resized_count} optimized, {elapsed:.1f}s elapsed)...")

    elapsed = time.time() - t0
    saved_bytes = max(0, total_orig - total_new)
    savings_pct = (100.0 * saved_bytes / total_orig) if total_orig > 0 else 0.0

    print(f"[+] Optimization Complete in {elapsed:.1f}s:")
    print(f"    - Total Images: {total_files} ({resized_count} resized to <={max_w}x{max_h})")
    print(f"    - Original Size: {total_orig / (1024*1024):.2f} MB")
    print(f"    - Optimized Size: {total_new / (1024*1024):.2f} MB")
    print(f"    - Bandwidth & Storage Saved: {saved_bytes / (1024*1024):.2f} MB ({savings_pct:.1f}% reduction)")

    return {
        "status": "ok",
        "total_files": total_files,
        "resized_count": resized_count,
        "orig_mb": total_orig / (1024 * 1024),
        "new_mb": total_new / (1024 * 1024),
        "saved_mb": saved_bytes / (1024 * 1024),
        "savings_pct": savings_pct,
        "elapsed_sec": elapsed,
    }


def main():
    media_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MEDIA_DIR
    optimize_all_media_images(media_dir)


if __name__ == "__main__":
    main()
