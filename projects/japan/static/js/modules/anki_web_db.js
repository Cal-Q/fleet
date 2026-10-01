// static/js/modules/anki_web_db.js — IndexedDB Offline Cache & Database Engine
// Strictly <= 200 lines, <= 100 cols invariant.

import { ankiLog } from './anki_logger.js';
import {
  applySchedulerOfflineTransition,
  computeDeckCountsFromCards,
  getOfflineTodayDays
} from './anki_web_scheduler_offline.js';
import { computeLocalRollupCounts } from './anki_deck_rollup.js';
export { queueReview, getOutboxCount, flushReviewOutbox } from './anki_web_outbox.js';

const DB_NAME = 'anki_offline_db';
const DB_VERSION = 1;
let _dbPromise = null;

export function getDB() {
  if (!_dbPromise) {
    _dbPromise = new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains('meta')) {
          db.createObjectStore('meta', { keyPath: 'key' });
        }
        if (!db.objectStoreNames.contains('deck_cards')) {
          db.createObjectStore('deck_cards', { keyPath: 'did' });
        }
        if (!db.objectStoreNames.contains('outbox')) {
          db.createObjectStore('outbox', { keyPath: 'id', autoIncrement: true });
        }
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
      const tx = db.transaction('meta', 'readonly');
      const req = tx.objectStore('meta').get('decks');
      req.onsuccess = () => resolve(req.result ? req.result.data : null);
      req.onerror = () => resolve(null);
    });
  } catch {
    return null;
  }
}

export async function cacheDeckCards(did, cards, counts, fingerprint = null) {
  try {
    const normDid = Number(did);
    const db = await getDB();
    const existing = await getCachedDeckCards(normDid);
    let finalCards = cards;
    let finalFp = fingerprint || existing?.fingerprint || null;
    if (existing?.cards?.length && existing.cards.length > cards.length) {
      const cardMap = new Map(existing.cards.map((c) => [c.id, c]));
      for (const fc of cards) {
        cardMap.set(fc.id, { ...(cardMap.get(fc.id) || {}), ...fc });
      }
      finalCards = Array.from(cardMap.values());
      finalFp = existing.fingerprint || finalFp;
    }
    const entry = {
      did: normDid,
      cards: finalCards,
      counts,
      updated: Date.now()
    };
    if (finalFp) entry.fingerprint = finalFp;
    const tx = db.transaction('deck_cards', 'readwrite');
    tx.objectStore('deck_cards').put(entry);
    ankiLog('DATA', 'CACHE', 'CACHE_CARDS_SAVED', {
      did: normDid,
      count: finalCards.length,
      fingerprint: finalFp
    });
  } catch (e) {
    ankiLog('WARN', 'CACHE', 'CACHE_CARDS_FAIL', { did, err: String(e) });
  }
}

export async function getCachedDeckCards(did) {
  try {
    const normDid = Number(did);
    const db = await getDB();
    return new Promise((res) => {
      const tx = db.transaction('deck_cards', 'readonly');
      const req = tx.objectStore('deck_cards').get(normDid);
      req.onsuccess = () => res(req.result || null);
      req.onerror = () => res(null);
    });
  } catch {
    return null;
  }
}

export async function saveLocalSettings(settings) {
  try {
    const db = await getDB();
    const tx = db.transaction('meta', 'readwrite');
    tx.objectStore('meta').put({
      key: 'app_settings',
      data: settings,
      updated: Date.now()
    });
  } catch {}
}

export async function getLocalSettings() {
  try {
    const db = await getDB();
    return new Promise((resolve) => {
      const tx = db.transaction('meta', 'readonly');
      const req = tx.objectStore('meta').get('app_settings');
      req.onsuccess = () => resolve(req.result ? req.result.data : null);
      req.onerror = () => resolve(null);
    });
  } catch {
    return null;
  }
}

export async function updateCachedCardReview(did, cardId, grade) {
  try {
    const db = await getDB();
    const tx = db.transaction('deck_cards', 'readwrite');
    const store = tx.objectStore('deck_cards');
    const td = getOfflineTodayDays();
    const normDid = did ? Number(did) : 0;

    const updateRecord = (rec) => {
      if (!rec || !rec.cards || !Array.isArray(rec.cards)) return false;
      const idx = rec.cards.findIndex((c) => c.id === cardId);
      if (idx === -1) return false;
      applySchedulerOfflineTransition(rec.cards[idx], grade, td);
      rec.counts = computeDeckCountsFromCards(rec.cards, td);
      store.put(rec);
      return true;
    };

    if (normDid) {
      const req = store.get(normDid);
      req.onsuccess = () => {
        if (req.result && updateRecord(req.result)) return;
        const allReq = store.getAll();
        allReq.onsuccess = () => {
          for (const r of (allReq.result || [])) {
            if (r.did !== normDid && updateRecord(r)) break;
          }
        };
      };
    } else {
      const allReq = store.getAll();
      allReq.onsuccess = () => {
        for (const r of (allReq.result || [])) {
          if (updateRecord(r)) break;
        }
      };
    }
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
