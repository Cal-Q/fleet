#!/usr/bin/env python3
"""
scripts/chrome_cdp.py — Lightweight pure-Python Chrome DevTools Protocol Client
Strictly <= 200 lines invariant.
"""

import json
import os
import re
import socket
import struct
import subprocess
import time
import urllib.request


def encode_frame(payload_bytes: bytes) -> bytes:
    length = len(payload_bytes)
    frame = bytearray([0x81])
    mask_key = b"\x12\x34\x56\x78"
    if length <= 125:
        frame.append(0x80 | length)
    elif length <= 65535:
        frame.append(0x80 | 126)
        frame.extend(struct.pack("!H", length))
    else:
        frame.append(0x80 | 127)
        frame.extend(struct.pack("!Q", length))
    frame.extend(mask_key)
    masked = bytearray(payload_bytes[i] ^ mask_key[i % 4] for i in range(length))
    frame.extend(masked)
    return bytes(frame)


def recv_frame(s, initial_buf=b""):
    buf = bytearray(initial_buf)
    while True:
        while len(buf) < 2:
            chunk = s.recv(4096)
            if not chunk:
                return None, b""
            buf.extend(chunk)
        b1, b2, pos, length = buf[0], buf[1], 2, buf[1] & 0x7F
        if length == 126:
            while len(buf) < pos + 2:
                chunk = s.recv(4096)
                if not chunk:
                    return None, b""
                buf.extend(chunk)
            length, pos = struct.unpack("!H", buf[pos:pos+2])[0], pos + 2
        elif length == 127:
            while len(buf) < pos + 8:
                chunk = s.recv(4096)
                if not chunk:
                    return None, b""
                buf.extend(chunk)
            length, pos = struct.unpack("!Q", buf[pos:pos+8])[0], pos + 8
        while len(buf) < pos + length:
            chunk = s.recv(4096)
            if not chunk:
                return None, b""
            buf.extend(chunk)
        payload = bytes(buf[pos:pos+length])
        remainder = bytes(buf[pos+length:])
        if b1 & 0x0F == 0x01:
            return payload.decode("utf-8", "ignore"), remainder
        buf = bytearray(remainder)


class ChromeRunner:
    def __init__(self, target_url="https://japan.calq.it/anki", port=9222):
        self.target_url = target_url
        self.port = port
        self.proc = None
        self.sock = None
        self.rem = b""
        self.msg_id = 100

    def start(self):
        cands = [
            os.environ.get("CHROME_BIN"),
            "/home/japan/.cache/ms-playwright/chromium-1243/chrome-linux-arm64/chrome",
            "/snap/bin/chromium",
            "/usr/bin/chromium-browser",
            "chromium",
        ]
        chrome_bin = next((c for c in cands if c and os.path.exists(c)), "chromium")
        cmd = [
            chrome_bin,
            f"--app={self.target_url}",
            "--headless=new",
            f"--remote-debugging-port={self.port}",
            f"--user-data-dir=/tmp/chrome-offline-e2e-{int(time.time())}",
            "--disable-gpu",
            "--no-sandbox"
        ]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ws_url = None
        for _ in range(25):
            time.sleep(0.4)
            try:
                resp = urllib.request.urlopen(
                    f"http://127.0.0.1:{self.port}/json/list", timeout=2
                )
                tabs = json.loads(resp.read().decode())
                for t in tabs:
                    if t.get("type") == "page" and "webSocketDebuggerUrl" in t:
                        ws_url = t["webSocketDebuggerUrl"]
                        break
                if ws_url:
                    break
            except Exception:
                pass
        if not ws_url:
            raise RuntimeError("Failed to connect to Chromium CDP endpoint")
        m = re.search(r"ws://127\.0\.0\.1:\d+/(.*)", ws_url)
        path = "/" + m.group(1) if m else "/devtools/page/1"
        self.sock = socket.socket()
        self.sock.connect(("127.0.0.1", self.port))
        key = "dGhlIHNhbXBsZSBub25jZQ=="
        handshake = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{self.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(handshake.encode())
        hs = b""
        while b"\r\n\r\n" not in hs:
            hs += self.sock.recv(1024)
        self.rem = hs.split(b"\r\n\r\n", 1)[1]

    def send(self, method: str, params: dict = None, timeout: float = 15.0) -> any:
        self.msg_id += 1
        target_id = self.msg_id
        payload = json.dumps({"id": target_id, "method": method, "params": params or {}})
        self.sock.sendall(encode_frame(payload.encode()))
        t0 = time.time()
        while time.time() - t0 < timeout:
            msg, self.rem = recv_frame(self.sock, self.rem)
            if not msg:
                time.sleep(0.02)
                continue
            try:
                data = json.loads(msg)
                if data.get("id") == target_id:
                    return data.get("result")
            except Exception:
                pass
        return None

    def evaluate(self, expr: str, await_promise: bool = True, timeout: float = 15.0) -> any:
        params = {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": await_promise,
        }
        res = self.send("Runtime.evaluate", params, timeout=timeout)
        if res and isinstance(res, dict) and "result" in res:
            return res.get("result", {}).get("value")
        return None

    def emulate_mobile(self, width: int = 393, height: int = 851, dpr: float = 2.75):
        self.send("Emulation.setDeviceMetricsOverride", {
            "width": width, "height": height, "deviceScaleFactor": dpr, "mobile": True
        })
        self.send("Emulation.setTouchEmulationEnabled", {"enabled": True})

    def set_cpu_throttling(self, rate: int = 1):
        self.send("Emulation.setCPUThrottlingRate", {"rate": max(1, int(rate))})

    def emulate_offline(self, offline: bool = True):
        self.send("Network.enable", {})
        self.send("Network.emulateNetworkConditions", {
            "offline": offline,
            "latency": 0,
            "downloadThroughput": -1 if not offline else 0,
            "uploadThroughput": -1 if not offline else 0
        })

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        if self.proc:
            try:
                self.proc.terminate()
            except Exception:
                pass
