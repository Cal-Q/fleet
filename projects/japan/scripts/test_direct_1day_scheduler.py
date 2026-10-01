#!/usr/bin/env python3
"""
scripts/test_direct_1day_scheduler.py
Empirical proof of 1-Day Direct Scheduling on Redmi Note 7.
"""
import socket
import json
import struct
import time
import os
import sqlite3
import sys

def find_active_socket():
    try:
        with open("/proc/net/unix", "r") as f:
            for line in f:
                if "@webview_devtools_remote_" in line:
                    s_name = line.strip().split()[-1]
                    return s_name.replace("@", "\x00").encode()
    except Exception:
        pass
    return b"\x00webview_devtools_remote_17333"

def get_page_id():
    for _ in range(5):
        try:
            sock_name = find_active_socket()
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(2.0)
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
            if pages:
                return pages[0]["id"], sock_name
        except Exception:
            time.sleep(0.4)
    return None, None

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
    if not pid:
        return None
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(4.0)
    raw = bytearray()
    try:
        s.connect(sock_name)
        req = (f"GET /devtools/page/{pid} HTTP/1.1\r\nHost: localhost\r\n"
               f"Upgrade: websocket\r\nConnection: Upgrade\r\n"
               f"Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
               f"Sec-WebSocket-Version: 13\r\n\r\n").encode()
        s.sendall(req)
        s.recv(1024)
        cmd = json.dumps({"id": 1, "method": "Runtime.evaluate",
                          "params": {"expression": expr, "returnByValue": True,
                                     "awaitPromise": True}})
        s.sendall(encode_frame(cmd.encode()))
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            raw.extend(chunk)
            if len(raw) >= 2:
                plen = raw[1] & 0x7F
                needed = 2 + plen
                if plen == 126 and len(raw) >= 4:
                    needed = 4 + struct.unpack("!H", raw[2:4])[0]
                elif plen == 127 and len(raw) >= 10:
                    needed = 10 + struct.unpack("!Q", raw[2:10])[0]
                if len(raw) >= needed:
                    break
    except Exception as e:
        print("cdp error:", e)
    finally:
        s.close()
    if len(raw) < 2:
        return None
    plen = raw[1] & 0x7F
    offset = 2
    if plen == 126:
        offset = 4
    elif plen == 127:
        offset = 10
    try:
        parsed = json.loads(raw[offset:].decode("utf-8", "ignore"))
        return parsed.get("result", {}).get("result", {}).get("value")
    except Exception:
        return None

def take_screencap(outpath):
    os.system(f"env -i /system/bin/screencap -p {outpath}")

def run_test():
    print("[1] Hard resetting webview...")
    cdp_eval("window.ankiHardReset && window.ankiHardReset();")
    time.sleep(1.8)

    print("[2] Opening deck overview & starting session...")
    cdp_eval(
        "window.ankiOpenDeckOverview(1786908932593, 'Lingua Inglese • Linguistica', 7, 3, 24);"
    )
    time.sleep(0.4)
    cdp_eval("window.ankiLaunchStudySession();")
    time.sleep(0.6)

    card1 = cdp_eval("window.ankiGetCurrentCard ? window.ankiGetCurrentCard() : null;")
    print(f"Card 1: id={card1.get('id') if card1 else None}, "
          f"queue={card1.get('queue') if card1 else None}")

    print("[3] Flipping card to verify intervals...")
    cdp_eval("window.ankiFlipCard();")
    time.sleep(0.3)
    ivl_wrong = cdp_eval("document.getElementById('ankiIvlWrong')?.innerText")
    ivl_correct = cdp_eval("document.getElementById('ankiIvlCorrect')?.innerText")
    print(f"Intervals on Card 1: Wrong={ivl_wrong} (Expected '1g'), Correct={ivl_correct}")

    print("[4] Answering 'Again / Wrong' (Grade 1)...")
    cdp_eval("window.ankiAnswerCard(1);")
    time.sleep(0.6)

    card2 = cdp_eval("window.ankiGetCurrentCard ? window.ankiGetCurrentCard() : null;")
    print(f"Card 2 (Next): id={card2.get('id') if card2 else None}, "
          f"queue={card2.get('queue') if card2 else None}")

    if card1 and card1.get("id"):
        cid = card1["id"]
        db_path = "/data/data/com.termux/files/home/japan/data/collection.anki2"
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT crt FROM col LIMIT 1")
        col_crt = cur.fetchone()[0]
        today_days = int((int(time.time()) - col_crt) / 86400)
        cur.execute("SELECT queue, due, ivl, factor, reps, lapses FROM cards WHERE id = ?", (cid,))
        row = cur.fetchone()
        conn.close()
        print(f"DB Record for Card 1 ({cid}): queue={row[0]} (2=review), "
              f"due={row[1]} (today+1={today_days+1}), ivl={row[2]} (1 day), lapses={row[5]}")

    take_screencap("/data/local/tmp/screen_direct_1day_study.png")
    print("Screenshot captured to /data/local/tmp/screen_direct_1day_study.png")

if __name__ == "__main__":
    run_test()
