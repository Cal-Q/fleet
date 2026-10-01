// static/js/modules/anki_web_media.js — Offline Card Media Pre-fetcher & Cache Storage
// Strictly <= 200 lines invariant.

import { ankiLog } from './anki_logger.js';

export async function prefetchCardMedia(cards, onProgress = null) {
  if (!cards || !Array.isArray(cards) || !('caches' in window) || !navigator.onLine) return;
  const urls = new Set();
  const imgRegex = /<img[^>]+src=["']([^"']+)["']/g;
  for (const c of cards) {
    for (const f of [c.front, c.notes, c.ruby_all, c.reading, c.meaning]) {
      if (!f) continue;
      imgRegex.lastIndex = 0;
      let match;
      while ((match = imgRegex.exec(f)) !== null) {
        if (match[1] && match[1].startsWith('/media/')) urls.add(match[1]);
      }
    }
  }
  if (urls.size === 0) return;
  try {
    const cacheKeys = await caches.keys();
    const activeCache = cacheKeys.find(k => k.startsWith('anki-pwa-')) || 'anki-pwa-v30';
    const cache = await caches.open(activeCache);
    const urlList = Array.from(urls);
    const concurrency = 4;
    let completed = 0;
    const pool = [];

    for (const u of urlList) {
      let p;
      p = (async () => {
        try {
          const cached = await cache.match(u, { ignoreSearch: true });
          if (!cached && navigator.onLine) {
            const res = await fetch(u);
            if (res && res.status === 200) await cache.put(u, res);
          }
        } catch {}
        completed++;
        const idx = pool.indexOf(p);
        if (idx !== -1) pool.splice(idx, 1);
        if (onProgress) onProgress(completed, urlList.length);
      })();
      pool.push(p);
      if (pool.length >= concurrency) await Promise.race(pool);
    }
    await Promise.all(pool);
    ankiLog('DATA', 'CACHE', 'PREFETCH_MEDIA_DONE', { count: urlList.length });
  } catch {}
}
