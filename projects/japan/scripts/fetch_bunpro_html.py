"""
Bunpro Grammar Point Full HTML Extractor.

Asynchronously downloads complete HTML pages (including Next.js __NEXT_DATA__)
for all 979 Bunpro grammar points, saving them locally for offline parsing.
"""

import argparse
import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Dict, Tuple
import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("bunpro_extractor")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
}


def make_safe_filename(gp_id: int, title: str) -> str:
    """Create a clean filesystem-safe filename preserving Japanese characters."""
    safe_title = re.sub(r'[/\\?%*:|"<>\s]', "_", title).strip("_")
    return f"{gp_id:04d}_{safe_title}.html"


async def fetch_single_point(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    item: Dict,
    out_dir: Path,
    delay: float,
    force: bool = False,
) -> Tuple[str, int, str]:
    """Download a single grammar point HTML with retries and rate limiting."""
    gp_id = item["id"]
    filename = make_safe_filename(gp_id, item.get("title", f"gp_{gp_id}"))
    out_path = out_dir / filename

    if not force and out_path.exists() and out_path.stat().st_size > 1024:
        return "skipped", gp_id, filename

    url = item.get("url")
    if not url:
        return "no_url", gp_id, filename

    for attempt in range(1, 4):
        try:
            async with sem:
                if delay > 0:
                    await asyncio.sleep(delay)
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=25)) as resp:
                    if resp.status == 200:
                        text = await resp.text(encoding="utf-8", errors="replace")
                        if '<script id="__NEXT_DATA__"' in text:
                            out_path.write_text(text, encoding="utf-8")
                            return "ok", gp_id, filename
                        logger.warning(f"[GP {gp_id}] HTTP 200 but __NEXT_DATA__ missing (try {attempt})")
                    elif resp.status == 429:
                        wait = 6 * attempt
                        logger.warning(f"[GP {gp_id}] 429 Rate Limit. Backing off {wait}s...")
                        await asyncio.sleep(wait)
                    else:
                        logger.warning(f"[GP {gp_id}] Status {resp.status} (try {attempt})")
        except Exception as exc:
            logger.warning(f"[GP {gp_id}] Network error: {exc} (try {attempt})")
            await asyncio.sleep(2 * attempt)

    return "failed", gp_id, filename


async def run_extraction(
    points_path: Path, out_dir: Path, concurrency: int, delay: float, limit: int = 0, force: bool = False
) -> None:
    """Orchestrate concurrent extraction across all grammar points."""
    with open(points_path, "r", encoding="utf-8") as f:
        points = json.load(f)

    if limit > 0:
        points = points[:limit]

    out_dir.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(concurrency)
    connector = aiohttp.TCPConnector(limit=concurrency + 2, ssl=False)
    total = len(points)

    logger.info(f"Extracting {total} grammar points into {out_dir} (workers: {concurrency}, delay: {delay}s)")
    stats = {"ok": 0, "skipped": 0, "failed": 0, "no_url": 0}

    async with aiohttp.ClientSession(headers=HEADERS, connector=connector) as session:
        tasks = [fetch_single_point(session, sem, pt, out_dir, delay, force) for pt in points]
        completed = 0
        for future in asyncio.as_completed(tasks):
            status, _, _ = await future
            stats[status] = stats.get(status, 0) + 1
            completed += 1
            if completed % 25 == 0 or completed == total:
                logger.info(
                    f"Progress: [{completed}/{total}] "
                    f"(OK: {stats['ok']}, Skipped: {stats['skipped']}, Failed: {stats['failed']})"
                )

    logger.info("=" * 50)
    logger.info(f"Done! Total: {total} | OK: {stats['ok']} | Skipped: {stats['skipped']} | Failed: {stats['failed']}")


def main():
    parser = argparse.ArgumentParser(description="Extract all Bunpro Grammar Points full HTML")
    parser.add_argument("--points", type=Path, default=Path("japanese/bunpro_grammar_points.json"))
    parser.add_argument("--out-dir", type=Path, default=Path("japanese/bunpro_raw_html"))
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--delay", type=float, default=0.15)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--force", action="store_true")

    args = parser.parse_args()
    asyncio.run(
        run_extraction(
            points_path=args.points,
            out_dir=args.out_dir,
            concurrency=args.concurrency,
            delay=args.delay,
            limit=args.limit,
            force=args.force,
        )
    )


if __name__ == "__main__":
    main()
