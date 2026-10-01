// static/sw_anki.js — Service Worker for AnkiDroid Web (100% Offline PWA)
// Strictly <= 200 lines invariant.

const CODE_CACHE_NAME = 'anki-code-v2.10.16';
const MEDIA_CACHE_NAME = 'anki-media-v1';

const CODE_ASSETS = [
  '/anki',
  '/manifest_anki.json',
  '/static/manifest_anki.json',
  '/static/js/anki_bundle.js',
  '/static/js/modules/anki_web_ui.js',
  '/static/js/modules/anki_study_runner.js',
  '/static/js/modules/anki_study_session.js',
  '/static/js/modules/anki_study_status_views.js',
  '/static/js/modules/anki_web_reviewer.js',
  '/static/js/modules/anki_web_bindings.js',
  '/static/js/modules/anki_web_study.js',
  '/static/js/modules/anki_web_gestures.js',
  '/static/js/modules/anki_card_animator.js',
  '/static/js/modules/anki_web_keybindings.js',
  '/static/js/modules/anki_card_rule_hints.js',
  '/static/js/modules/anki_web_db.js',
  '/static/js/modules/anki_web_outbox.js',
  '/static/js/modules/anki_web_scheduler_offline.js',
  '/static/js/modules/anki_web_settings.js',
  '/static/js/modules/anki_web_timer.js',
  '/static/js/modules/anki_timer_render.js',
  '/static/js/modules/anki_web_session_timer.js',
  '/static/js/modules/anki_web_session_timer_ui.js',
  '/static/js/modules/anki_web_fatigue.js',
  '/static/js/modules/anki_fatigue_neural.js',
  '/static/js/modules/anki_fatigue_telemetry.js',
  '/static/js/modules/anki_fatigue_snapshot.js',
  '/static/js/modules/anki_fatigue_eval.js',
  '/static/js/modules/anki_web_audio.js',
  '/static/js/modules/anki_web_decks.js',
  '/static/js/modules/anki_deck_rollup.js',
  '/static/js/modules/anki_deck_prefetch.js',
  '/static/js/modules/anki_deck_render.js',
  '/static/js/modules/anki_deck_overview.js',
  '/static/js/modules/anki_web_updater.js',
  '/static/js/modules/anki_updater_ui.js',
  '/static/js/modules/anki_web_queue.js',
  '/static/js/modules/anki_web_meanings.js',
  '/static/js/modules/anki_web_persistence.js',
  '/static/js/modules/anki_logger.js',
  '/static/js/modules/anki_log_viewer.js',
  '/static/js/modules/bunki.js'
];

const MEDIA_ASSETS = [
  '/media/_HGSKyokashotai.ttf',
  '/static/icon-192.png',
  '/static/icon-512.png',
  '/static/css/tailwind.min.css'
];

self.addEventListener('message', (e) => {
  if (e.data?.type === 'SKIP_WAITING') self.skipWaiting();
});

self.addEventListener('install', (e) => {
  e.waitUntil(
    Promise.all([
      caches.open(CODE_CACHE_NAME).then((c) => c.addAll(CODE_ASSETS).catch(() => {})),
      caches.open(MEDIA_CACHE_NAME).then(async (c) => {
        for (const u of MEDIA_ASSETS) {
          const match = await c.match(u, { ignoreSearch: true });
          if (!match) await c.add(u).catch(() => {});
        }
      })
    ]).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((k) => {
          if (k === MEDIA_CACHE_NAME || k === CODE_CACHE_NAME) return Promise.resolve();
          if (k.startsWith('anki-code-') || k.startsWith('anki-pwa-')) return caches.delete(k);
          return Promise.resolve();
        })
      );
    }).then(() => self.clients.claim())
  );
});

function fetchWithTimeout(request, ms = 2500) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), ms);
  return fetch(request, { signal: ctrl.signal }).finally(() => clearTimeout(t));
}

self.addEventListener('fetch', (e) => {
  const req = e.request;
  const url = new URL(req.url);

  if (req.method !== 'GET' || url.protocol === 'chrome-extension:') return;

  // Let API calls pass directly to network so IndexedDB handles offline fallback cleanly
  if (url.pathname.startsWith('/api/')) return;

  // 1. /anki HTML: Network first with fast timeout, fallback to offline cache
  if (url.pathname === '/anki') {
    e.respondWith(
      fetchWithTimeout(req, 2500).then((res) => {
        if (res && res.status === 200) {
          const copy = res.clone();
          caches.open(CODE_CACHE_NAME).then((c) => c.put('/anki', copy));
        }
        return res;
      }).catch(async () => {
        const match = await caches.match('/anki');
        const fallback = new Response('Offline - Anki PWA', {
          status: 200,
          headers: { 'Content-Type': 'text/html' }
        });
        return match || fallback;
      })
    );
    return;
  }

  // 2. JS bundle & modules: Network first with fast timeout, fallback to cached for offline
  const isModule = url.pathname.startsWith('/static/js/modules/');
  const isBundle = url.pathname === '/static/js/anki_bundle.js';
  if (isModule || isBundle) {
    e.respondWith(
      fetchWithTimeout(req, 2500).then((res) => {
        if (res && res.status === 200) {
          const copy = res.clone();
          caches.open(CODE_CACHE_NAME).then((c) => {
            c.put(req, copy.clone());
            c.put(url.pathname, copy);
          });
        }
        return res;
      }).catch(async () => {
        const reqMatch = await caches.match(req);
        const pathMatch = await caches.match(url.pathname, { ignoreSearch: true });
        return reqMatch || pathMatch;
      })
    );
    return;
  }

  // 3. TPU model weights: Permanent media cache first
  if (url.pathname.startsWith('/static/data/')) {
    e.respondWith(
      (async () => {
        const cache = await caches.open(MEDIA_CACHE_NAME);
        const cached = await cache.match(url.pathname);
        if (cached) return cached;
        try {
          const res = await fetch(req);
          if (res && res.status === 200) cache.put(url.pathname, res.clone());
          return res;
        } catch {
          return caches.match(url.pathname);
        }
      })()
    );
    return;
  }

  // 4. Static assets & Media (kanji images, fonts, icons, tailwind, manifest)
  const isStatic = url.pathname.startsWith('/static/');
  const isMedia = url.pathname.startsWith('/media/');
  const isManifest = url.pathname.includes('manifest');
  if (isStatic || isMedia || isManifest) {
    e.respondWith(
      (async () => {
        const cache = await caches.open(MEDIA_CACHE_NAME);
        const decPath = decodeURIComponent(url.pathname);
        const cached = (await cache.match(req, { ignoreSearch: true })) ||
                       (await cache.match(url.pathname, { ignoreSearch: true })) ||
                       (await cache.match(decPath, { ignoreSearch: true }));
        if (cached) return cached;

        try {
          const res = await fetchWithTimeout(req, 4000);
          if (res && res.status === 200) {
            cache.put(req, res.clone());
            cache.put(url.pathname, res.clone());
            if (decPath !== url.pathname) cache.put(decPath, res.clone());
          }
          return res;
        } catch {
          return new Response('', { status: 404, statusText: 'Offline asset not in cache' });
        }
      })()
    );
    return;
  }
});
