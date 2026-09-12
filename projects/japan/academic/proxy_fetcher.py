#!/usr/bin/env python3
"""
MEXT & Japanese Embassy Web Scraper / Proxy Fetcher
Routes requests through the verified Fujitsu Futro proxy setup to bypass Akamai Bot Manager blocks.
"""

import os
import sys
import subprocess
import argparse
from urllib.parse import urlparse

DEFAULT_URL = "https://www.it.emb-japan.go.jp/itpr_it/studio_JapaneseStudies.html"
PROXY_SOCKS5 = "socks5h://127.0.0.1:1080"


def fetch_via_futro_ssh(url, output_file=None):
    """Executes curl_cffi on futro directly over SSH for bulletproof Akamai bypass."""
    script = f"""
from curl_cffi import requests
import sys

url = "{url}"
try:
    r = requests.get(url, impersonate="chrome124", timeout=30)
    if r.status_code == 200:
        sys.stdout.buffer.write(r.content)
    else:
        sys.stderr.write(f"HTTP Error: {{r.status_code}}\\n")
        sys.exit(1)
except Exception as e:
    sys.stderr.write(f"Fetch failed: {{e}}\\n")
    sys.exit(1)
"""
    cmd = [
        "sudo", "ssh", "-F", "/root/.ssh/config", "futro",
        f"python3 -c '{script}'"
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
        if res.returncode != 0:
            print(f"⚠️ Errore fetch remoto SSH: {res.stderr.decode('utf-8', errors='replace')}")
            return False, res.stderr
        
        content = res.stdout
        if output_file:
            os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
            with open(output_file, "wb") as f:
                f.write(content)
            print(f"✅ File scaricato con successo: {output_file} ({len(content)} bytes)")
        else:
            try:
                print(content.decode("utf-8")[:1000])
            except UnicodeDecodeError:
                print(f"File binario scaricato: {len(content)} bytes")
        return True, content
    except Exception as e:
        print(f"Errore durante l'esecuzione del proxy fetcher: {e}")
        return False, str(e).encode()


def main():
    parser = argparse.ArgumentParser(description="MEXT & Embassy Proxy Scraper (via Fujitsu Futro)")
    parser.add_argument("url", nargs="?", default=DEFAULT_URL, help="URL da scaricare (default: pagina borsa Japanese Studies Ambasciata)")
    parser.add_argument("-o", "--output", help="Percorso del file in cui salvare il risultato")
    args = parser.parse_args()

    print(f"🌐 Connessione in corso a: {args.url} (tramite proxy Fujitsu Futro)...")
    success, _ = fetch_via_futro_ssh(args.url, args.output)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
