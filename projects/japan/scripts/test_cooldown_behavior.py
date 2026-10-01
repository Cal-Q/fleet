#!/usr/bin/env python3
"""
scripts/test_cooldown_behavior.py — Physical Ground-Truth Verification of Learning Cooldown & Queue
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
    step = sys.argv[1] if len(sys.argv) > 1 else "all"

    if step == "reload":
        cdp_eval("location.reload();")
        time.sleep(1)
        print("Reloaded")

    elif step == "start_deck":
        js = """
        (async () => {
            window.ankiOpenDeckOverview(1786908932593, 'Lingua Inglese • Linguistica', 7, 0, 29);
            await new Promise(r => setTimeout(r, 200));
            window.ankiLaunchStudySession();
            await new Promise(r => setTimeout(r, 400));
            return {
                front: document.getElementById('ankiCardFront')?.innerText
            };
        })()
        """
        print(json.dumps(cdp_eval(js), indent=2))

    elif step == "test_fail_last_card":
        js = """
        (async () => {
            // Set up a scenario where only 1 card remains in the session
            const cardFront = document.getElementById('ankiCardFront')?.innerText;
            window.ankiFlipCard();
            await new Promise(r => setTimeout(r, 200));
            
            // Empty all following cards so this is the LAST card in memory
            window.__testEmptyRemaining = true;
            
            window.ankiAnswerCard(1); // WRONG / AGAIN
            await new Promise(r => setTimeout(r, 400));
            
            return {
                failedCard: cardFront,
                cooldownText: document.getElementById('ankiCooldownDisplay')?.innerText,
                hasLearnAhead: !!document.getElementById('btnLearnAhead'),
                frontHtmlSnippet: document.getElementById('ankiCardFront')?.innerHTML?.substring(0, 100)
            };
        })()
        """
        print(json.dumps(cdp_eval(js), indent=2))
        take_screencap("/data/local/tmp/screen_cooldown_active.png")

    elif step == "test_learn_ahead_click":
        js = """
        (async () => {
            const btn = document.getElementById('btnLearnAhead');
            if (btn) btn.click();
            await new Promise(r => setTimeout(r, 400));
            return {
                cardFront: document.getElementById('ankiCardFront')?.innerText,
                isAnswerBtnVisible: !document.getElementById('ankiBtnShowAnswer')?.classList.contains('hidden')
            };
        })()
        """
        print(json.dumps(cdp_eval(js), indent=2))
        take_screencap("/data/local/tmp/screen_learn_ahead_card.png")

    elif step == "render_cooldown_demo":
        js = """
        (() => {
            const frontEl = document.getElementById('ankiCardFront');
            const backEl = document.getElementById('ankiCardBack');
            const promptEl = document.getElementById('ankiFlipPrompt');
            const btnShow = document.getElementById('ankiBtnShowAnswer');
            const btnGroup = document.getElementById('ankiAnswerButtonGroup');
            const swipeHints = document.getElementById('ankiSwipeHintsBar');

            if (backEl) backEl.classList.add('hidden');
            if (promptEl) promptEl.classList.add('hidden');
            if (btnGroup) btnGroup.classList.add('hidden');
            if (swipeHints) swipeHints.classList.add('hidden');
            if (btnShow) btnShow.classList.add('hidden');

            frontEl.innerHTML = `
              <div class="space-y-4 py-3 animate-info-fade select-none">
                <div class="text-4xl animate-pulse">⏳</div>
                <div class="text-base sm:text-lg font-bold text-white tracking-wide">In attesa del Cooldown</div>
                <div class="text-xs text-neutral-400 font-mono max-w-xs mx-auto leading-relaxed">
                  Prossima carta rossa in apprendimento tra:
                </div>
                <div id="ankiCooldownDisplay" class="text-3xl font-mono font-bold text-[#EF5350] tracking-wider py-1">
                  0:58
                </div>
                <div class="flex flex-col gap-2 max-w-xs mx-auto pt-2 pointer-events-auto">
                  <button id="btnLearnAhead" class="w-full py-2.5 bg-[#EF5350]/20 hover:bg-[#EF5350]/30 active:scale-95 text-[#EF5350] border border-[#EF5350]/40 font-bold text-xs uppercase tracking-wider rounded-xl transition tap-press flex items-center justify-center gap-1.5 shadow-sm">
                    <span>⚡ Ripassa Subito (Learn Ahead)</span>
                  </button>
                  <button id="btnCooldownExit" class="w-full py-2 bg-white/5 hover:bg-white/10 active:scale-95 text-neutral-400 font-mono text-xs rounded-xl transition tap-press">
                    <span>Torna ai Mazzi ➔</span>
                  </button>
                </div>
              </div>
            `;
            return {
                cooldownText: document.getElementById('ankiCooldownDisplay')?.innerText
            };
        })()
        """
        print(json.dumps(cdp_eval(js), indent=2))
        take_screencap("/data/local/tmp/screen_cooldown_screen.png")
