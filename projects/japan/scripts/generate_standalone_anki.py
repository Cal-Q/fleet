#!/usr/bin/env python3
"""
scripts/generate_standalone_anki.py — Generate Inlined Standalone anki.html
Pre-renders all Jinja2 components and seeds decks/settings into raw HTML for offline Kiosk APK.
Strictly <= 200 lines invariant.
"""

import os
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

import jinja2
from core.anki_engine import fetch_anki_decks_data
from core.anki_settings_store import get_persisted_settings


def generate_standalone_anki(out_path: str = None) -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_dir = os.path.join(base_dir, "templates")

    if not out_path:
        out_path = os.path.join(base_dir, "static", "anki_standalone.html")

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(templates_dir),
        autoescape=False
    )
    template = env.get_template("anki.html")

    try:
        decks = fetch_anki_decks_data().get("decks", [])
    except Exception as e:
        print(f"[!] Warning: failed to fetch live decks: {e}", file=sys.stderr)
        decks = []

    settings = get_persisted_settings(base_dir)

    rendered = template.render(decks=decks, settings=settings)

    if "{% include" in rendered or "{%" in rendered:
        raise ValueError("Unrendered Jinja2 tags detected in rendered output!")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(rendered)

    print(f"[✓] Successfully generated standalone anki HTML ({len(rendered)} bytes, {len(decks)} decks): {out_path}")
    return out_path


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    generate_standalone_anki(target)
