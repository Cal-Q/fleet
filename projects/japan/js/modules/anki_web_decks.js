// static/js/modules/anki_web_decks.js — Deck List Lifecycle, Prefetch & Overview
// Strictly <= 200 lines, <= 100 cols invariant.

import { ankiLog } from './anki_logger.js';
import {
  cacheDecks, getCachedDecks, flushReviewOutbox
} from './anki_web_db.js';
import {
  renderDecks as renderDecksDom, toggleDeckCollapse as toggleDeckCollapseDom,
  toggleAllDecksCollapse as toggleAllDecksCollapseDom
} from './anki_deck_render.js';
import { openDeckOverview as openDeckOverviewDom } from './anki_deck_overview.js';
import { stopCardTimer } from './anki_web_timer.js';
import { setCurrentDeck, showView } from './anki_web_study.js';
import {
  getAllCachedDeckRecords, computeLocalRollupCounts
} from './anki_deck_rollup.js';
import { prefetchDeckCards, updateSyncProgressBar } from './anki_deck_prefetch.js';

export { prefetchDeckCards, updateSyncProgressBar };

let _decks = [];
const get = (id) => document.getElementById(id);

const getSyncDecks = () => {
  if (Array.isArray(window?.__INITIAL_DECKS__) && window.__INITIAL_DECKS__.length) {
    return window.__INITIAL_DECKS__;
  }
  try {
    const raw = localStorage.getItem('anki_cached_decks');
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
};

const persistDecksSync = (d) => {
  try {
    if (d?.length) localStorage.setItem('anki_cached_decks', JSON.stringify(d));
  } catch {}
};

_decks = getSyncDecks();
if (_decks.length > 0) cacheDecks(_decks);

export function getDecksList() {
  return _decks;
}

export async function refreshDecksFromLocalCache() {
  const records = await getAllCachedDeckRecords();
  if (records.length > 0 && _decks.length > 0) {
    _decks = computeLocalRollupCounts(_decks, records);
    persistDecksSync(_decks);
    renderDecks();
  }
  return _decks;
}

if (typeof window !== 'undefined') {
  window.__ankiOnDeckCountsChanged = (updatedDecks) => {
    if (Array.isArray(updatedDecks) && updatedDecks.length > 0) {
      _decks = updatedDecks;
      const listEl = document.getElementById('ankiDeckListView');
      if (listEl && !listEl.classList.contains('hidden')) {
        renderDecks();
      }
    }
  };
}

export function renderDecks(force = false) {
  if (!_decks || _decks.length === 0) _decks = getSyncDecks();
  renderDecksDom(_decks, force);
}

export const toggleDeckCollapse = (name) =>
  toggleDeckCollapseDom(_decks, name, () => renderDecks(true));

export const toggleAllDecksCollapse = (collapse) =>
  toggleAllDecksCollapseDom(_decks, collapse, () => renderDecks(true));

export async function loadDecksListImpl(forcePrefetch = false) {
  stopCardTimer();
  setCurrentDeck(null, '');
  showView('deckList');
  const title = get('ankiAppTitle');
  if (title) title.innerText = 'Japan Mastery • Mazzi';
  get('ankiNavBackBtn')?.classList.add('hidden');
  get('ankiTopDuePill')?.classList.add('hidden');
  ankiLog('ACTION', 'NAV', 'SHOW_DECK_LIST', {});

  renderDecks();

  getCachedDecks().then(async (c) => {
    if (c?.length) {
      _decks = c;
      await refreshDecksFromLocalCache();
    }
  });

  if (navigator.onLine) {
    try {
      await flushReviewOutbox();
      const res = await fetch('/api/anki/decks');
      if (res.ok) {
        const data = await res.json();
        if (data?.decks?.length > 0) {
          const records = await getAllCachedDeckRecords();
          _decks = (records.length > 0)
            ? computeLocalRollupCounts(data.decks, records)
            : data.decks;
          persistDecksSync(_decks);
          cacheDecks(_decks);
          renderDecks();
          if (forcePrefetch) {
            prefetchDeckCards(_decks, true, () => refreshDecksFromLocalCache());
          }
        }
      }
    } catch (err) {
      ankiLog('WARN', 'NET', 'DECKS_FETCH_FAILED_FALLBACK_CACHE', { error: String(err) });
      await refreshDecksFromLocalCache();
    }
  } else {
    await refreshDecksFromLocalCache();
  }
}

export const openDeckOverview = (did, name, n = null, l = null, r = null) =>
  openDeckOverviewDom(_decks, did, name, n, l, r);

export const forceSyncDecks = () => loadDecksListImpl(true);
