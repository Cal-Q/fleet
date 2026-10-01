#!/usr/bin/env python3
"""
core/anki_micro_server.py — Zero-Dependency Local Anki Server
Runs on pure Python standard library (http.server) for instant local execution.
Strictly <= 200 lines invariant.
"""

import json, mimetypes, os, re, sys, urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

_script_dir = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.dirname(_script_dir) if os.path.basename(_script_dir) == "core" else _script_dir
if WORKSPACE_DIR not in sys.path: sys.path.insert(0, WORKSPACE_DIR)

from core.anki_engine import fetch_anki_decks_data, get_deck_cards
from core.anki_settings_store import get_persisted_settings, save_persisted_settings
from core.anki_sm2 import apply_sm2_review
from core.db import open_anki_db


class AnkiHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filepath, content_type=None):
        if not os.path.exists(filepath):
            self.send_error(404, "File not found")
            return
        if content_type is None:
            content_type, _ = mimetypes.guess_type(filepath)
            content_type = content_type or "application/octet-stream"
        with open(filepath, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)

        if path in ["/", "/anki", "/anki/"]:
            html_path = os.path.join(WORKSPACE_DIR, "templates", "anki.html")
            if not os.path.exists(html_path):
                html_path = os.path.join(WORKSPACE_DIR, "anki.html")
            with open(html_path, "r", encoding="utf-8") as f:
                content = f.read()
            try:
                decks_data = fetch_anki_decks_data().get("decks", [])
                content = content.replace("{{ (decks or []) | tojson | safe }}", json.dumps(decks_data))
                settings_data = get_persisted_settings(WORKSPACE_DIR)
                content = content.replace("{{ (settings or {}) | tojson | safe }}", json.dumps(settings_data))
            except Exception:
                content = content.replace("{{ (decks or []) | tojson | safe }}", "[]")
                content = content.replace("{{ (settings or {}) | tojson | safe }}", "{}")
            body = content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path.startswith("/static/"):
            rel = path[len("/static/"):]
            fpath = os.path.join(WORKSPACE_DIR, "static", rel)
            self._send_file(fpath)
            return

        if path.startswith("/media/"):
            rel = urllib.parse.unquote(path[len("/media/"):])
            media_dirs = [
                os.path.join(WORKSPACE_DIR, ".local/share/Anki2/User 1/collection.media"),
                "/sdcard/AnkiDroid/collection.media",
                "/data/local/tmp/collection.media"
            ]
            for md in media_dirs:
                mp = os.path.join(md, rel)
                if os.path.exists(mp):
                    self._send_file(mp)
                    return
            self.send_error(404, "Media not found")
            return

        if path == "/api/anki/decks":
            try: self._send_json(fetch_anki_decks_data())
            except Exception as e: self._send_json({"status": "error", "error": str(e)}, 500)
            return

        if path == "/api/anki/deck_cards":
            did, limit = int(qs.get("did", [0])[0]), int(qs.get("limit", [100])[0])
            try: self._send_json(get_deck_cards(did, limit))
            except Exception as e: self._send_json({"status": "error", "error": str(e)}, 500)
            return

        if path == "/api/anki/settings":
            self._send_json({"status": "ok", "settings": get_persisted_settings(WORKSPACE_DIR)})
            return

        if path == "/api/anki/version":
            up = os.path.join(WORKSPACE_DIR, "static", "js", "modules", "anki_web_updater.js")
            ver, bld = "v2.5.2", "20260922_v252"
            if os.path.exists(up):
                try:
                    with open(up, "r", encoding="utf-8") as f: src = f.read()
                    vm, bm = re.search(r"CURRENT_VERSION\s*=\s*['\"]([^'\"]+)['\"]", src), re.search(r"CURRENT_BUILD\s*=\s*['\"]([^'\"]+)['\"]", src)
                    if vm: ver = vm.group(1)
                    if bm: bld = bm.group(1)
                except Exception: pass
            self._send_json({"status": "ok", "version": ver, "build": bld, "release_date": "2026-09-22",
                "changelog": ["AI Neurale: continuo recupero stato latente post micro-pausa", "Single source of truth per il versioning"]})
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"

        if path == "/api/anki/settings":
            try:
                cur = get_persisted_settings(WORKSPACE_DIR)
                payload = json.loads(raw_body)
                if "deck_timers" in payload and isinstance(payload["deck_timers"], dict):
                    cur_timers = cur.get("deck_timers", {})
                    cur_timers.update(payload["deck_timers"])
                    payload["deck_timers"] = cur_timers
                cur.update(payload)
                ok = save_persisted_settings(WORKSPACE_DIR, cur)
                self._send_json({"status": "ok" if ok else "error", "settings": cur})
            except Exception as e:
                self._send_json({"status": "error", "error": str(e)}, 500)
            return

        if path == "/api/anki/review":
            try:
                payload = json.loads(raw_body)
                card_id = int(payload.get("card_id", 0))
                grade = int(payload.get("grade", 0))
                time_ms = int(payload.get("time_ms", 0))
                conn = open_anki_db()
                res = apply_sm2_review(conn, card_id, grade, time_ms)
                conn.close()
                self._send_json(res)
            except Exception as e:
                self._send_json({"status": "error", "error": str(e)}, 500)
            return

        if path in ["/api/anki/log", "/api/anki/client_logs"]:
            try:
                payload = json.loads(raw_body)
                log_file = os.path.join(WORKSPACE_DIR, "logs", "anki_client_events.jsonl")
                os.makedirs(os.path.dirname(log_file), exist_ok=True)
                events = payload.get("events") or payload.get("logs") or [payload]
                with open(log_file, "a", encoding="utf-8") as f:
                    for ev in events:
                        f.write(json.dumps(ev, ensure_ascii=False) + "\n")
                self._send_json({"status": "ok", "received": len(events)})
            except Exception as e:
                self._send_json({"status": "error", "error": str(e)}, 500)
            return

        self.send_error(404, "Not Found")

    def log_message(self, format, *args):
        pass


def run_server(port: int = 3033):
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, AnkiHandler)
    print(f"[*] Anki Micro-Server running at http://127.0.0.1:{port}/anki")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    p = int(sys.argv[1]) if len(sys.argv) > 1 else 3033
    run_server(p)
