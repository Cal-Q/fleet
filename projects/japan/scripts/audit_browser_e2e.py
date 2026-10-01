#!/usr/bin/env python3
"""
scripts/audit_browser_e2e.py — Deterministic Multi-Area Headless Browser Test Suite
Enforces Invariant 34 across all 5 stages and interactive UI components.
Strictly <= 200 lines invariant.
"""

import json
import os
import re
import socket
import struct
import subprocess
import sys
import time
import urllib.request


def encode_frame(payload_bytes: bytes) -> bytes:
    length = len(payload_bytes)
    frame = bytearray([0x81])
    mask_key = b"\x12\x34\x56\x78"
    if length <= 125: frame.append(0x80 | length)
    elif length <= 65535: frame.append(0x80 | 126); frame.extend(struct.pack("!H", length))
    else: frame.append(0x80 | 127); frame.extend(struct.pack("!Q", length))
    frame.extend(mask_key)
    masked = bytearray(payload_bytes[i] ^ mask_key[i % 4] for i in range(length))
    frame.extend(masked)
    return bytes(frame)


def recv_frame(s, initial_buf=b""):
    buf = bytearray(initial_buf)
    while True:
        while len(buf) < 2:
            chunk = s.recv(4096)
            if not chunk: return None, b""
            buf.extend(chunk)
        b1, b2, pos, length = buf[0], buf[1], 2, buf[1] & 0x7F
        if length == 126:
            while len(buf) < pos + 2:
                chunk = s.recv(4096)
                if not chunk: return None, b""
                buf.extend(chunk)
            length, pos = struct.unpack("!H", buf[pos:pos+2])[0], pos + 2
        elif length == 127:
            while len(buf) < pos + 8:
                chunk = s.recv(4096)
                if not chunk: return None, b""
                buf.extend(chunk)
            length, pos = struct.unpack("!Q", buf[pos:pos+8])[0], pos + 8
        while len(buf) < pos + length:
            chunk = s.recv(4096)
            if not chunk: return None, b""
            buf.extend(chunk)
        payload = bytes(buf[pos:pos+length])
        remainder = bytes(buf[pos+length:])
        if b1 & 0x0F == 0x01:
            return payload.decode("utf-8", "ignore"), remainder
        buf = bytearray(remainder)


class ChromeE2E:
    def __init__(self, target_url="https://japan.calq.it/"):
        self.target_url = target_url
        self.proc = None
        self.sock = None
        self.rem = b""
        self.msg_id = 100
    def start(self):
        p_chrome = "/home/japan/.cache/puppeteer/chrome/linux_arm-153.0.8010.36/chrome-linux-arm64/chrome"
        chrome_bin = os.environ.get("CHROME_BIN") or (p_chrome if os.path.exists(p_chrome) else ("/snap/bin/chromium" if os.path.exists("/snap/bin/chromium") else "chromium-browser"))
        cmd = [chrome_bin, f"--app={self.target_url}", "--headless=new", "--remote-debugging-port=9222", "--user-data-dir=/tmp/chrome-e2e-test", "--disable-gpu", "--no-sandbox"]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ws_url = None
        for _ in range(15):
            time.sleep(0.5)
            try:
                tabs = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json/list", timeout=2).read().decode())
                for t in tabs:
                    if t.get("type") == "page" and "webSocketDebuggerUrl" in t:
                        ws_url = t["webSocketDebuggerUrl"]
                        break
                if ws_url: break
            except Exception:
                pass
        m = re.search(r"ws://127\.0\.0\.1:9222/(.*)", ws_url)
        path = "/" + m.group(1) if m else "/devtools/page/1"
        self.sock = socket.socket()
        self.sock.connect(("127.0.0.1", 9222))
        handshake = f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1:9222\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\n\r\n"
        self.sock.sendall(handshake.encode())
        hs = b""
        while b"\r\n\r\n" not in hs: hs += self.sock.recv(1024)
        self.rem = hs.split(b"\r\n\r\n", 1)[1]

    def evaluate(self, expr: str) -> any:
        self.msg_id += 1
        payload = json.dumps({"id": self.msg_id, "method": "Runtime.evaluate", "params": {"expression": expr, "returnByValue": True, "awaitPromise": True}})
        self.sock.sendall(encode_frame(payload.encode()))
        for _ in range(20):
            msg, self.rem = recv_frame(self.sock, self.rem)
            if not msg: break
            try:
                data = json.loads(msg)
                if data.get("id") == self.msg_id:
                    return data.get("result", {}).get("result", {}).get("value")
            except Exception:
                pass
        return None

    def close(self):
        if self.sock:
            try: self.sock.close()
            except Exception: pass
        if self.proc:
            self.proc.terminate()


def run_e2e_audit():
    print("[*] Starting Deterministic Multi-Area Browser E2E Audit...")
    runner = ChromeE2E("https://japan.calq.it/")
    runner.start()
    try:
        for _ in range(20):
            time.sleep(0.3)
            if runner.evaluate("document.readyState") == "complete": break

        # Area 1: Platform Boot
        title = runner.evaluate("document.title")
        print(f" [+] Area 1: Platform Boot -> Title: '{title}'")
        assert "MEXT" in str(title) or "japan" in str(title).lower(), f"Unexpected title: {title}"

        # Area 2: Daily Routine Stage
        routine_ok = runner.evaluate("Boolean(document.getElementById('stage_routine'))")
        print(f" [+] Area 2: Daily Routine Stage -> Present: {routine_ok}")
        assert routine_ok, "Stage Routine missing from DOM"

        # Area 3: Study Studio & Sub-Branches
        runner.evaluate("window.switchTab('study')")
        study_ok = runner.evaluate("Boolean(document.getElementById('stage_study'))")
        runner.evaluate("window.switchStudyBranch('vocab')")
        v_ok = runner.evaluate("Boolean(document.getElementById('branch_btn_vocab'))")
        runner.evaluate("window.switchStudyBranch('grammar')")
        g_ok = runner.evaluate("Boolean(document.getElementById('branch_btn_grammar'))")
        print(f" [+] Area 3: Study Studio (Kanji/Vocab/Grammar) -> Present: {study_ok}, Branches: {v_ok and g_ok}")
        assert study_ok and v_ok and g_ok, "Study Studio stage/branches failed"

        # Area 4: Exam Lab — Single Question Runner, Option Select, Quick Jump & Notes
        runner.evaluate("window.switchTab('exams'); window.loadExam('A');")
        time.sleep(0.5)
        q_count = runner.evaluate("document.querySelectorAll('#examQuestionRail button').length")
        q_text = runner.evaluate("document.querySelector('#examSingleContainer .jp-mincho')?.innerText")
        task_badge = runner.evaluate("document.querySelector('#examSingleContainer span.font-bold.text-neutral-700')?.innerText")
        print(f" [+] Area 4.1: Exam Lab Rail -> Found {q_count} quick-jump buttons")
        print(f" [+] Area 4.2: Active Question -> Task: '{task_badge}', Text: '{q_text}'")
        assert q_count >= 12 and q_text, "Exam question rail or text missing"

        runner.evaluate("document.querySelector('.exam-opt-card')?.click()")
        opt_sel = runner.evaluate("Boolean(document.querySelector('.exam-opt-card')?.className.includes('181A1B'))")
        print(f" [+] Area 4.3: Tactile Option Select -> Option active: {opt_sel}")
        assert opt_sel, "Option card active state not triggered"

        init_note = runner.evaluate("Boolean(document.getElementById('noteDrawer') && !document.getElementById('noteDrawer').classList.contains('hidden'))")
        toggled_note = runner.evaluate("window.toggleCurrentNote(); Boolean(document.getElementById('noteDrawer') && !document.getElementById('noteDrawer').classList.contains('hidden'))")
        print(f" [+] Area 4.4: Collapsible Note Drawer -> Initial: {init_note}, Toggled: {toggled_note}")
        assert init_note != toggled_note, "Note drawer did not toggle state"

        txt = runner.evaluate("window.nextQuestion(); document.querySelector('#examSingleContainer')?.innerText")
        print(f" [+] Area 4.5: Navigation Advance -> Has Q.02: {'Q.02' in str(txt)}")
        assert "Q.02" in str(txt), f"Expected Q.02 in card text, got: {str(txt)[:80]}"

        # Area 5: Dossier & Strategy Stage (Esse3, Fascicolo, Ricerca)
        runner.evaluate("window.switchTab('dossier')")
        d_ok = runner.evaluate("Boolean(document.getElementById('stage_dossier'))")
        runner.evaluate("window.switchDossierBranch('checklist')")
        chk_ok = runner.evaluate("Boolean(document.getElementById('branch_btn_dossier_checklist'))")
        runner.evaluate("window.switchDossierBranch('research')")
        res_ok = runner.evaluate("Boolean(document.getElementById('branch_btn_dossier_research'))")
        print(f" [+] Area 5: Dossier & Research Archive Stage -> Present: {d_ok}, Branches: {chk_ok and res_ok}")
        assert d_ok and chk_ok and res_ok, "Stage Dossier or branches missing from DOM"

        print("\n[🎉] ALL MULTI-AREA BROWSER E2E CHECKS PASSED DETERMINISTICALLY!")
        return True
    finally:
        runner.close()


if __name__ == "__main__":
    success = run_e2e_audit()
    sys.exit(0 if success else 1)
