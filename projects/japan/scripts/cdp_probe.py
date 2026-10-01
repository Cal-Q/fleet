#!/usr/bin/env python3
import socket, json, struct, sys, subprocess, re

def find_socket():
    res = subprocess.check_output(['su', '-c', 'grep -a webview_devtools_remote /proc/net/unix']).decode('utf-8', 'ignore')
    m = re.search(r'(@webview_devtools_remote_\d+)', res)
    if m:
        return '\0' + m.group(1)[1:]
    raise RuntimeError('No active webview socket found')

def get_page_id(sock_name):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(sock_name)
    s.sendall(b"GET /json HTTP/1.1\r\nHost: localhost\r\n\r\n")
    res = b""
    while True:
        chunk = s.recv(4096)
        if not chunk: break
        res += chunk
        if b"]" in res: break
    s.close()
    parts = res.split(b"\r\n\r\n", 1)
    if len(parts) < 2: return "1"
    pages = json.loads(parts[1].decode("utf-8", "ignore"))
    for p in pages:
        if p.get("type") == "page":
            return p.get("id")
    return pages[0]["id"] if pages else "1"

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
    sock_name = find_socket()
    pid = get_page_id(sock_name)
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(sock_name)
    req = (f"GET /devtools/page/{pid} HTTP/1.1\r\nHost: localhost\r\n"
           f"Upgrade: websocket\r\nConnection: Upgrade\r\n"
           f"Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\n\r\n").encode()
    s.sendall(req)
    s.recv(1024)
    cmd = json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": expr, "returnByValue": True, "awaitPromise": True}})
    s.sendall(encode_frame(cmd.encode()))
    raw = s.recv(65536)
    s.close()
    payload_len = raw[1] & 0x7F
    offset = 2
    if payload_len == 126: offset = 4
    elif payload_len == 127: offset = 10
    parsed = json.loads(raw[offset:].decode("utf-8", "ignore"))
    return parsed.get("result", {}).get("result", {}).get("value")

if __name__ == "__main__":
    expr = sys.argv[1] if len(sys.argv) > 1 else "document.title"
    res = cdp_eval(expr)
    print(json.dumps(res, indent=2, ensure_ascii=False))
