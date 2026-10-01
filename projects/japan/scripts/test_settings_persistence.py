#!/usr/bin/env python3
import socket
import json
import struct
import time
import subprocess
import sys

def find_active_socket():
    with open("/proc/net/unix", "r") as f:
        for line in f:
            if "@webview_devtools_remote_" in line:
                s_name = line.strip().split()[-1]
                return s_name.replace("@", "\x00").encode()
    return b"\x00webview_devtools_remote_1810"

def get_page_id():
    sock_name = find_active_socket()
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(sock_name)
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
            return p.get("id"), sock_name
    return pages[0]["id"], sock_name

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
    pid, sock_name = get_page_id()
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(sock_name)
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
    action = sys.argv[1] if len(sys.argv) > 1 else "verify_restored_settings"

    if action == "set_custom_settings":
        js = """
        (async () => {
            window.ankiOpenDeckSettings(1786908932593, 'Lingua Inglese • Linguistica');
            await new Promise(r => setTimeout(r, 100));
            window.ankiSetCardTimerPreset(10);
            
            window.ankiSetFrontFontSize(42);
            window.ankiSetBackFontSize(22);
            window.ankiSetFuriganaMode('always');
            window.ankiSetSessionPreset(35);
            
            await new Promise(r => setTimeout(r, 600));
            
            return {
                localDeckTimers: localStorage.getItem('anki_deck_timers'),
                localFrontSize: localStorage.getItem('anki_front_font_size'),
                localFurigana: localStorage.getItem('anki_furigana_mode'),
                localSessionTarget: localStorage.getItem('anki_session_target_min')
            };
        })()
        """
        res = cdp_eval(js)
        print("Set custom settings result:", json.dumps(res, indent=2))

    elif action == "wipe_local_and_reload":
        js = """
        (async () => {
            localStorage.clear();
            location.replace('/anki?t=' + Date.now());
        })()
        """
        cdp_eval(js)
        print("LocalStorage cleared and page reloaded")
        time.sleep(2)

    elif action == "verify_restored_settings":
        js = """
        (async () => {
            await new Promise(r => setTimeout(r, 1000));
            
            window.ankiOpenDeckSettings(1786908932593, 'Lingua Inglese • Linguistica');
            await new Promise(r => setTimeout(r, 300));
            
            const cardTimerText = document.getElementById('ankiModalCardTimerDisplay')?.innerText;
            const sessionTimerInput = document.getElementById('ankiModalCustomMinInput')?.value;
            const frontFontSize = localStorage.getItem('anki_front_font_size');
            const furiganaMode = localStorage.getItem('anki_furigana_mode');
            const deckTimers = localStorage.getItem('anki_deck_timers');
            
            return {
                cardTimerText,
                sessionTimerInput,
                frontFontSize,
                furiganaMode,
                deckTimers,
                modalVisible: !document.getElementById('ankiSessionTimerModal')?.classList.contains('hidden')
            };
        })()
        """
        res = cdp_eval(js)
        print("Restored settings evaluation:", json.dumps(res, indent=2))
        take_screencap("/data/local/tmp/screen_deck_settings_persisted.png")

    elif action == "open_settings_panel":
        js = """
        (async () => {
            window.ankiCloseSessionTimerModal();
            await new Promise(r => setTimeout(r, 200));
            window.ankiToggleSettings(true);
            await new Promise(r => setTimeout(r, 200));
            return {
                panelVisible: !document.getElementById('ankiSettingsPanel')?.classList.contains('hidden')
            };
        })()
        """
        res = cdp_eval(js)
        print("Settings panel opened:", json.dumps(res, indent=2))
        take_screencap("/data/local/tmp/screen_settings_panel_persisted.png")

