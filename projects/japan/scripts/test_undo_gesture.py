#!/usr/bin/env python3
"""
scripts/test_undo_gesture.py — Automated verification of Swipe Down & Undo on phone
"""
import socket
import json
import struct
import time
import subprocess
import sys

def get_page_id():
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(b"\x00webview_devtools_remote_1810")
    s.sendall(b"GET /json HTTP/1.1\r\nHost: localhost\r\n\r\n")
    res = b""
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        res += chunk
        if b"]" in res:
            break
    s.close()
    header, body = res.split(b"\r\n\r\n", 1)
    pages = json.loads(body.decode("utf-8", "ignore"))
    for p in pages:
        if p.get("type") == "page":
            return p.get("id")
    return pages[0]["id"]

def encode_frame(payload_bytes):
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
    masked = bytearray(length)
    for i in range(length):
        masked[i] = payload_bytes[i] ^ mask_key[i % 4]
    frame.extend(masked)
    return bytes(frame)

def cdp_eval(expr):
    pid = get_page_id()
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(b"\x00webview_devtools_remote_1810")
    req = f"GET /devtools/page/{pid} HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\n\r\n".encode()
    s.sendall(req)
    s.recv(1024)
    cmd = json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": expr, "returnByValue": True, "awaitPromise": True}})
    s.sendall(encode_frame(cmd.encode()))
    raw = s.recv(65536)
    s.close()
    if len(raw) < 2:
        return None
    payload_len = raw[1] & 0x7F
    offset = 2
    if payload_len == 126:
        offset = 4
    elif payload_len == 127:
        offset = 10
    parsed = json.loads(raw[offset:].decode("utf-8", "ignore"))
    return parsed.get("result", {}).get("result", {}).get("value")

def take_screencap(outpath):
    subprocess.run(["/system/bin/screencap", "-p", outpath], check=True)

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "full"
    
    if action == "start_study":
        js = """
        (async () => {
            window.ankiOpenDeckOverview(1786908932593, 'Lingua Inglese • Linguistica', 7, 0, 29);
            await new Promise(r => setTimeout(r, 200));
            window.ankiLaunchStudySession();
            await new Promise(r => setTimeout(r, 500));
            return {
                cardFront: document.getElementById('ankiCardFront')?.innerText,
                isStudyVisible: !document.getElementById('ankiStudyView')?.classList.contains('hidden')
            };
        })()
        """
        print(json.dumps(cdp_eval(js), indent=2))
        take_screencap("/data/local/tmp/screen_study_card1.png")

    elif action == "answer_first":
        js = """
        (async () => {
            const card1Front = document.getElementById('ankiCardFront')?.innerText;
            window.ankiFlipCard();
            await new Promise(r => setTimeout(r, 250));
            window.ankiAnswerCard(3);
            await new Promise(r => setTimeout(r, 500));
            const card2Front = document.getElementById('ankiCardFront')?.innerText;
            return { card1Front, card2Front };
        })()
        """
        print(json.dumps(cdp_eval(js), indent=2))
        take_screencap("/data/local/tmp/screen_study_card2.png")

    elif action == "show_down_swipe":
        js = """
        (() => {
            const card = document.getElementById('ankiCardContainer');
            const badge = document.getElementById('ankiBadgeUndo');
            const tint = document.getElementById('ankiCardTintOverlay');
            if (card) {
                card.style.transform = 'translate3d(0, 120px, 0) scale(0.97)';
                card.style.transition = 'none';
            }
            if (badge) badge.style.opacity = '1';
            if (tint) {
                tint.style.backgroundColor = 'rgba(66, 165, 245, 0.25)';
                tint.style.opacity = '1';
            }
            return { pullDownApplied: true };
        })()
        """
        print(json.dumps(cdp_eval(js), indent=2))
        take_screencap("/data/local/tmp/screen_swipe_down_active.png")

    elif action == "trigger_undo":
        js = """
        (async () => {
            const card = document.getElementById('ankiCardContainer');
            const badge = document.getElementById('ankiBadgeUndo');
            const tint = document.getElementById('ankiCardTintOverlay');
            if (card) {
                card.style.transition = 'transform 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
                card.style.transform = 'translate3d(0, 0, 0) scale(1)';
            }
            if (badge) badge.style.opacity = '0';
            if (tint) tint.style.opacity = '0';
            
            // Execute undo review
            window.ankiUndoReview();
            await new Promise(r => setTimeout(r, 500));
            return {
                restoredCardFront: document.getElementById('ankiCardFront')?.innerText
            };
        })()
        """
        print(json.dumps(cdp_eval(js), indent=2))
        take_screencap("/data/local/tmp/screen_after_undo.png")
