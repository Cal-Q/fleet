// static/js/modules/anki_deck_prefetch.js — Leaf Deck Offline Prefetcher & Sync Bar
// Strictly <= 200 lines, <= 100 cols invariant.

import { ankiLog } from './anki_logger.js';
import { cacheDeckCards, getCachedDeckCards } from './anki_web_db.js';
import { prefetchCardMedia } from './anki_web_media.js';
import { showGlobalBanner } from './anki_updater_ui.js';

let _isPrefetching = false;
const get = (id) => document.getElementById(id);

export function updateSyncProgressBar(current, total, label = '') {
  const container = get('ankiSyncProgressBarContainer');
  const bar = get('ankiSyncProgressBar');
  const txtPercent = get('ankiSyncProgressPercent');
  const txtStatus = get('ankiSyncProgressStatus');
  if (!container || !bar) return;

  if (total <= 0 || current >= total) {
    if (bar) bar.style.width = '100%';
    if (txtPercent) txtPercent.innerText = '100%';
    if (txtStatus) {
      txtStatus.innerHTML =
        '<span class="text-emerald-400 font-bold">✅ Sincronizzazione completata</span>';
    }
    setTimeout(() => container?.classList.add('hidden'), 2000);
    return;
  }

  container.classList.remove('hidden');
  const pct = Math.max(2, Math.min(99, Math.round((current / total) * 100)));
  if (bar) bar.style.width = `${pct}%`;
  if (txtPercent) txtPercent.innerText = `${pct}%`;
  if (txtStatus) {
    const spin = '<span class="animate-spin inline-block mr-1">🔄</span>';
    txtStatus.innerHTML = `${spin} ${label} (${current}/${total})`;
  }
}

function normalizeFp(fp) {
  if (!fp || typeof fp !== 'string') return '';
  const parts = fp.split('_');
  return parts.length >= 2 ? `${parts[0]}_${parts[1]}` : fp;
}

export async function prefetchDeckCards(decks, force = false, onComplete = null) {
  if (!decks || !Array.isArray(decks) || !navigator.onLine || _isPrefetching || !force) return;
  _isPrefetching = true;
  updateSyncProgressBar(0, 1, 'Verifica integrità mazzi...');
  try {
    const leafDecks = decks.filter((d) => !d.has_children && !d.is_master && d.total > 0);
    const decksToSync = [];

    for (const d of leafDecks) {
      if (force) {
        decksToSync.push(d);
        continue;
      }
      const c = await getCachedDeckCards(d.id);
      const isMatch = c?.cards?.length && c?.fingerprint && d.fingerprint &&
        normalizeFp(c.fingerprint) === normalizeFp(d.fingerprint);
      if (isMatch) continue;
      if (c?.cards?.length && d.total && c.cards.length >= d.total) {
        c.fingerprint = d.fingerprint;
        await cacheDeckCards(d.id, c.cards, c.counts, d.fingerprint);
        continue;
      }
      decksToSync.push(d);
    }

    if (decksToSync.length === 0) {
      ankiLog('DATA', 'CACHE', 'ALL_LEAF_DECKS_PRESERVED', { count: leafDecks.length });
      updateSyncProgressBar(1, 1, 'Mazzi sincronizzati');
      showGlobalBanner('✅ Mazzi sincronizzati (offline ok)', 1800, false);
      if (typeof onComplete === 'function') await onComplete();
      return;
    }

    const totalSteps = decksToSync.length;
    showGlobalBanner(`Sincronizzazione di ${totalSteps} mazzi...`, 0, true);
    updateSyncProgressBar(0, totalSteps, 'Sincronizzazione mazzi');
    let done = 0;

    for (const d of decksToSync) {
      const dName = d.display_name || d.leaf_name || d.name;
      updateSyncProgressBar(done, totalSteps, `Scaricamento ${dName}`);
      showGlobalBanner(`Scaricamento ${dName} (${done + 1}/${totalSteps})...`, 0, true);
      try {
        const res = await fetch(`/api/anki/deck_cards?did=${d.id}&full=true`);
        const data = res.ok ? await res.json() : null;
        if (data?.cards?.length) {
          const fp = data.fingerprint || d.fingerprint || null;
          await cacheDeckCards(d.id, data.cards, data.counts, fp);
          prefetchCardMedia(data.cards);
        }
      } catch {}
      done++;
      updateSyncProgressBar(done, totalSteps, `Scaricato ${dName}`);
    }
    updateSyncProgressBar(totalSteps, totalSteps, 'Completato');
    showGlobalBanner('✅ Sincronizzazione mazzi completata', 2500, false);
    if (typeof onComplete === 'function') await onComplete();
  } finally {
    _isPrefetching = false;
  }
}
