// static/js/modules/anki_web_media.js — Offline Card Media Pre-fetcher & Memory Staging
// Strictly <= 200 lines, <= 100 cols invariant.

import { ankiLog } from './anki_logger.js';

const _warmedUrls = new Set();

export function extractCardMediaUrls(cards) {
  const list = Array.isArray(cards) ? cards : (cards ? [cards] : []);
  const urls = new Set();
  const imgRegex = /<img[^>]+src=["']([^"']+)["']/g;

  for (const c of list) {
    if (!c) continue;
    for (const f of [c.front, c.notes, c.ruby_all, c.reading, c.meaning]) {
      if (!f) continue;
      imgRegex.lastIndex = 0;
      let match;
      while ((match = imgRegex.exec(f)) !== null) {
        const src = match[1];
        if (src && src.startsWith('/media/')) {
          urls.add(src);
        }
      }
    }
  }
  return Array.from(urls);
}

export function preloadImageInMemory(url) {
  if (!url || typeof Image === 'undefined' || _warmedUrls.has(url)) return;
  _warmedUrls.add(url);
  try {
    const img = new Image();
    img.decoding = 'async';
    img.src = url;
  } catch {}
}

export function preloadUpcomingCardImages(cards, startIndex = 0, lookaheadCount = 4) {
  if (!cards || !Array.isArray(cards)) return;
  const slice = cards.slice(startIndex, startIndex + lookaheadCount);
  const urls = extractCardMediaUrls(slice);
  for (const u of urls) {
    preloadImageInMemory(u);
  }
  if ('caches' in window) {
    prefetchUrlsToCache(urls).catch(() => {});
  }
}

async function prefetchUrlsToCache(urlList, onProgress = null) {
  if (!urlList.length || !('caches' in window)) return;
  try {
    const cache = await caches.open('anki-media-v1');
    const concurrency = 4;
    let completed = 0;
    const pool = [];

    for (const u of urlList) {
      let p;
      p = (async () => {
        try {
          const dec = decodeURIComponent(u);
          const cached = (
            (await cache.match(u, { ignoreSearch: true })) ||
            (await cache.match(dec, { ignoreSearch: true }))
          );
          if (!cached && navigator.onLine) {
            const res = await fetch(u);
            if (res && res.status === 200) {
              await cache.put(u, res.clone());
              if (dec !== u) {
                await cache.put(dec, res.clone());
              }
            }
          }
          preloadImageInMemory(u);
        } catch {}
        completed++;
        const idx = pool.indexOf(p);
        if (idx !== -1) pool.splice(idx, 1);
        if (typeof onProgress === 'function') {
          onProgress(completed, urlList.length);
        }
      })();
      pool.push(p);
      if (pool.length >= concurrency) {
        await Promise.race(pool);
      }
    }
    await Promise.all(pool);
  } catch {}
}

export async function prefetchCardMedia(cards, onProgress = null) {
  if (!cards || !('caches' in window) || !navigator.onLine) return;
  const urls = extractCardMediaUrls(cards);
  if (!urls.length) return;
  await prefetchUrlsToCache(urls, onProgress);
  ankiLog('DATA', 'CACHE', 'PREFETCH_MEDIA_DONE', { count: urls.length });
}
