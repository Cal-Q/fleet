"""CLI interface for converting DuelingBook replays into EDOPro (.yrp) files."""

import argparse
import json
import os
import sys
import urllib.request
from typing import Any, Dict

from .db_parser import DBLoader
from .translator import ReplayTranslator
from .yrp_writer import YrpWriter


def fetch_from_format_library(fl_id: int) -> Dict[str, Any]:
    """Fetches replay metadata from Format Library API."""
    url = f"https://formatlibrary.com/api/replays?id={fl_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        if isinstance(data, list) and data:
            return data[0]
        return data


def convert_file(input_path: str, output_path: str, game_num: int = 1) -> str:
    """Converts a local DuelingBook JSON file to an EDOPro .yrp file."""
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    loader = DBLoader()
    games = loader.parse(raw_data)

    if not games:
        raise ValueError("No valid games found in replay payload.")

    selected_game = games[0]
    for g in games:
        if g.game_number == game_num:
            selected_game = g
            break

    translator = ReplayTranslator(selected_game)
    yrp_meta = translator.convert_to_yrp()
    yrp_bytes = YrpWriter.pack(yrp_meta)

    with open(output_path, "wb") as f:
        f.write(yrp_bytes)

    return (
        f"Converted Game {selected_game.game_number}: "
        f"{selected_game.player1.username} vs {selected_game.player2.username} "
        f"({len(yrp_bytes)} bytes written to {output_path})"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert DuelingBook replay JSON into EDOPro .yrp replay binary."
    )
    parser.add_argument("--input", "-i", type=str, help="Path to DuelingBook replay JSON file")
    parser.add_argument("--output", "-o", type=str, default="output.yrp", help="Output .yrp path")
    parser.add_argument("--game", "-g", type=int, default=1, help="Game number in match to convert")
    parser.add_argument("--fl-id", type=int, help="Format Library Replay ID to fetch and inspect")

    args = parser.parse_args()

    if args.fl_id:
        print(f"Fetching replay ID {args.fl_id} from Format Library...")
        fl_meta = fetch_from_format_library(args.fl_id)
        print(json.dumps(fl_meta, indent=2))
        sys.exit(0)

    if not args.input:
        parser.print_help()
        sys.exit(1)

    try:
        summary = convert_file(args.input, args.output, args.game)
        print(f"SUCCESS: {summary}")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
