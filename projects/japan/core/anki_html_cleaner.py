#!/usr/bin/env python3
"""
core/anki_html_cleaner.py — Card HTML Sanitizer & High-Speed Media Staging
Ensures media tags are configured for eager preloading and fast async decoding.
Strictly <= 200 lines, <= 100 cols invariant.
"""
import re
import urllib.parse


def clean_html(raw: str) -> str:
    if not raw:
        return ""
    text = re.sub(r"<style[\s\S]*?</style>", "", raw).strip()

    def fix_img(m):
        src = m.group(1).strip()
        if not (
            src.startswith("http://") or src.startswith("https://") or src.startswith("/")
        ):
            src = f"/media/{urllib.parse.quote(src)}"
        return (
            f'<img src="{src}" loading="eager" fetchpriority="high" decoding="async" '
            f'class="max-h-56 max-w-full mx-auto rounded my-2 '
            f'object-contain inline-block shadow-md">'
        )

    text = re.sub(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', fix_img, text)

    def fix_sound(m):
        s_file = urllib.parse.quote(m.group(1).strip())
        btn_cls = (
            "inline-flex items-center gap-1.5 px-3 py-1 bg-[#2C2C2C] hover:bg-[#3C3C3C] "
            "rounded-full text-xs font-mono text-white transition tap-press my-1 "
            "border border-[#3C3C3C] shadow"
        )
        return (
            f'<button type="button" onclick="event.stopPropagation();'
            f'window.ankiPlayAudio(\'/media/{s_file}\')" class="{btn_cls}">'
            f'<span class="text-[#42A5F5]">▶</span> <span>Audio</span></button>'
        )

    return re.sub(r"\[sound:([^\]]+)\]", fix_sound, text)
