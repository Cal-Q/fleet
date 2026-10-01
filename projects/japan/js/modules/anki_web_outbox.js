// static/js/modules/anki_web_outbox.js — Offline Review Outbox Queue & Sync
// Strictly <= 200 lines, <= 100 cols invariant.

import { ankiLog } from './anki_logger.js';
import { getDB } from './anki_web_db.js';

export async function queueReview(reviewPayload) {
  try {
    const db = await getDB();
    const tx = db.transaction('outbox', 'readwrite');
    tx.objectStore('outbox').add({
      ...reviewPayload,
      timestamp: Date.now()
    });
    ankiLog('ACTION', 'CACHE', 'OUTBOX_REVIEW_QUEUED', reviewPayload);
  } catch (e) {
    ankiLog('ERROR', 'CACHE', 'OUTBOX_QUEUE_FAIL', {
      err: String(e),
      payload: reviewPayload
    });
  }
}

export async function getOutboxCount() {
  try {
    const db = await getDB();
    return new Promise((resolve) => {
      const tx = db.transaction('outbox', 'readonly');
      const req = tx.objectStore('outbox').count();
      req.onsuccess = () => resolve(req.result || 0);
      req.onerror = () => resolve(0);
    });
  } catch {
    return 0;
  }
}

export async function flushReviewOutbox() {
  try {
    const db = await getDB();
    const items = await new Promise((resolve) => {
      const tx = db.transaction('outbox', 'readonly');
      const req = tx.objectStore('outbox').getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => resolve([]);
    });
    if (!items.length) return 0;

    ankiLog('INFO', 'NET', 'FLUSH_OUTBOX_START', { count: items.length });
    const payload = {
      reviews: items.map((it) => ({
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
        ankiLog('INFO', 'CACHE', 'FLUSH_OUTBOX_SUCCESS', {
          synced: data.synced,
          count: items.length
        });
        return data.synced || items.length;
      }
    }
    return 0;
  } catch (err) {
    ankiLog('WARN', 'NET', 'FLUSH_OUTBOX_FAILED', { error: String(err) });
    return 0;
  }
}
