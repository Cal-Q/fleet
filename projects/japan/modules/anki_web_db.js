// static/js/modules/anki_web_db.js — IndexedDB Offline Cache, Settings & Review Outbox
// Strictly <= 200 lines invariant.

import { ankiLog } from './anki_logger.js';
import { applySm2OfflineTransition, computeDeckCountsFromCards, getOfflineTodayDays } from './anki_web_sm2_offline.js';

const DB_NAME = 'anki_offline_db';
const DB_VERSION = 1;
let _dbPromise = null;

function getDB() {
  if (!_dbPromise) {
    _dbPromise = new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains('meta')) db.createObjectStore('meta', { keyPath: 'key' });
        if (!db.objectStoreNames.contains('deck_cards')) db.createObjectStore('deck_cards', { keyPath: 'did' });
        if (!db.objectStoreNames.contains('outbox')) db.createObjectStore('outbox', { keyPath: 'id', autoIncrement: true });
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }
  return _dbPromise;
}

export async function cacheDecks(decks) {
  if (!decks || !Array.isArray(decks) || decks.length === 0) return;
  try {
    const db = await getDB();
    const tx = db.transaction('meta', 'readwrite');
    tx.objectStore('meta').put({ key: 'decks', data: decks, updated: Date.now() });
    ankiLog('DATA', 'CACHE', 'CACHE_DECKS_SAVED', { count: decks.length });
  } catch (e) {
    ankiLog('WARN', 'CACHE', 'CACHE_DECKS_FAIL', { err: String(e) });
  }
}

export async function getCachedDecks() {
  try {
    const db = await getDB();
    return new Promise((resolve) => {
      const req = db.transaction('meta', 'readonly').objectStore('meta').get('decks');
      req.onsuccess = () => resolve(req.result ? req.result.data : null);
      req.onerror = () => resolve(null);
    });
  } catch { return null; }
}

export async function cacheDeckCards(did, cards, counts, fingerprint = null) {
  try {
    const normDid = Number(did), db = await getDB();
    const entry = { did: normDid, cards, counts, updated: Date.now() };
    if (fingerprint) entry.fingerprint = fingerprint;
    db.transaction('deck_cards', 'readwrite').objectStore('deck_cards').put(entry);
    ankiLog('DATA', 'CACHE', 'CACHE_CARDS_SAVED', { did: normDid, count: cards.length, fingerprint });
  } catch (e) {
    ankiLog('WARN', 'CACHE', 'CACHE_CARDS_FAIL', { did, err: String(e) });
  }
}

export async function getCachedDeckCards(did) {
  try {
    const normDid = Number(did), db = await getDB();
    return new Promise((res) => {
      const req = db.transaction('deck_cards', 'readonly').objectStore('deck_cards').get(normDid);
      req.onsuccess = () => res(req.result || null);
      req.onerror = () => res(null);
    });
  } catch { return null; }
}

export async function saveLocalSettings(settings) {
  try {
    const db = await getDB();
    db.transaction('meta', 'readwrite').objectStore('meta').put({ key: 'app_settings', data: settings, updated: Date.now() });
  } catch {}
}

export async function getLocalSettings() {
  try {
    const db = await getDB();
    return new Promise((resolve) => {
      const req = db.transaction('meta', 'readonly').objectStore('meta').get('app_settings');
      req.onsuccess = () => resolve(req.result ? req.result.data : null);
      req.onerror = () => resolve(null);
    });
  } catch { return null; }
}

export async function queueReview(reviewPayload) {
  try {
    const db = await getDB();
    db.transaction('outbox', 'readwrite').objectStore('outbox').add({ ...reviewPayload, timestamp: Date.now() });
    ankiLog('ACTION', 'CACHE', 'OUTBOX_REVIEW_QUEUED', reviewPayload);
  } catch (e) {
    ankiLog('ERROR', 'CACHE', 'OUTBOX_QUEUE_FAIL', { err: String(e), payload: reviewPayload });
  }
}

export async function getOutboxCount() {
  try {
    const db = await getDB();
    return new Promise((resolve) => {
      const req = db.transaction('outbox', 'readonly').objectStore('outbox').count();
      req.onsuccess = () => resolve(req.result || 0);
      req.onerror = () => resolve(0);
    });
  } catch { return 0; }
}

export async function flushReviewOutbox() {
  try {
    const db = await getDB();
    const items = await new Promise((resolve) => {
      const req = db.transaction('outbox', 'readonly').objectStore('outbox').getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => resolve([]);
    });
    if (!items.length) return 0;
    ankiLog('INFO', 'NET', 'FLUSH_OUTBOX_START', { count: items.length });
    const payload = {
      reviews: items.map(it => ({
        card_id: it.card_id,
        grade: it.grade,
        time_ms: it.time_ms || 1000,
        review_time: it.timestamp || Date.now()
      }))
    };
    const res = await fetch('/api/anki/sync_offline_reviews', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      const data = await res.json();
      if (data?.status === 'ok') {
        const tx = db.transaction('outbox', 'readwrite');
        tx.objectStore('outbox').clear();
        ankiLog('INFO', 'CACHE', 'FLUSH_OUTBOX_SUCCESS', { synced: data.synced, count: items.length });
        return data.synced || items.length;
      }
    }
    return 0;
  } catch (err) {
    ankiLog('WARN', 'NET', 'FLUSH_OUTBOX_FAILED', { error: String(err) });
    return 0;
  }
}

export async function updateCachedCardReview(did, cardId, grade) {
  try {
    const db = await getDB(), normDid = Number(did);
    const tx = db.transaction(['deck_cards', 'meta'], 'readwrite');
    const store = tx.objectStore('deck_cards'), metaStore = tx.objectStore('meta');
    const td = getOfflineTodayDays();
    const req = (normDid && normDid > 0) ? store.get(normDid) : store.getAll();
    req.onsuccess = () => {
      const records = Array.isArray(req.result) ? req.result : (req.result ? [req.result] : []);
      for (const rec of records) {
        if (!rec.cards || !Array.isArray(rec.cards)) continue;
        const idx = rec.cards.findIndex(c => c.id === cardId);
        if (idx === -1) continue;
        applySm2OfflineTransition(rec.cards[idx], grade, td);
        rec.counts = computeDeckCountsFromCards(rec.cards, td);
        store.put(rec);
        ankiLog('DATA', 'CACHE', 'LOCAL_CARD_UPDATED', { did: rec.did, cid: cardId, counts: rec.counts });
        break;
      }
    };
    const metaReq = metaStore.get('decks');
    metaReq.onsuccess = () => {
      const entry = metaReq.result;
      if (entry && Array.isArray(entry.data)) {
        for (const d of entry.data) {
          if (d.id === did || did === 0) {
            if (d.review > 0) d.review--;
            else if (d.new > 0) d.new--;
            else if (d.learning > 0) d.learning--;
          }
        }
        metaStore.put(entry);
        try { localStorage.setItem('anki_cached_decks', JSON.stringify(entry.data)); } catch {}
      }
    };
  } catch (e) {
    ankiLog('WARN', 'CACHE', 'LOCAL_CARD_UPDATE_FAIL', { cid: cardId, err: String(e) });
  }
}

export async function clearCardCache() {
  try {
    const db = await getDB();
    const tx = db.transaction('deck_cards', 'readwrite');
    tx.objectStore('deck_cards').clear();
  } catch {}
}
