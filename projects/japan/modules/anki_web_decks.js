import { ankiLog } from './anki_logger.js';
import { cacheDecks, getCachedDecks, cacheDeckCards, getCachedDeckCards, flushReviewOutbox } from './anki_web_db.js';
import { computeDeckCountsFromCards } from './anki_web_sm2_offline.js';
import { prefetchCardMedia } from './anki_web_media.js';
import { setCurrentDeck, getSelectedDeck, showView } from './anki_web_study.js';
import { stopCardTimer } from './anki_web_timer.js';

let _decks = [];
let _selectedDeck = null;
let _collapsedDecks = new Set();

const get = id => document.getElementById(id);

let _hasPrefetched = false, _isPrefetching = false;

const getSyncDecks = () => {
  if (typeof window !== 'undefined' && Array.isArray(window.__INITIAL_DECKS__) && window.__INITIAL_DECKS__.length > 0) return window.__INITIAL_DECKS__;
  try { const raw = localStorage.getItem('anki_cached_decks'); if (raw) return JSON.parse(raw); } catch {}
  return [];
};

const persistDecksSync = (d) => { if (Array.isArray(d) && d.length > 0) try { localStorage.setItem('anki_cached_decks', JSON.stringify(d)); } catch {} };

_decks = getSyncDecks();
if (_decks.length > 0) { persistDecksSync(_decks); cacheDecks(_decks); }

const loadCollapsedSet = () => { try { const s = localStorage.getItem('anki_collapsed_decks'); return s ? new Set(JSON.parse(s)) : new Set(); } catch { return new Set(); } };
const saveCollapsedSet = (set) => { try { localStorage.setItem('anki_collapsed_decks', JSON.stringify([...set])); } catch {} };

_collapsedDecks = loadCollapsedSet();

export async function loadDecksListImpl(forcePrefetch = false) {
  stopCardTimer(); setCurrentDeck(null, ''); showView('deckList');
  if (get('ankiAppTitle')) get('ankiAppTitle').innerText = 'Japan Mastery • Mazzi';
  get('ankiNavBackBtn')?.classList.add('hidden'); get('ankiTopDuePill')?.classList.add('hidden');
  ankiLog('ACTION', 'NAV', 'SHOW_DECK_LIST', {});

  // 1. Instant Render from Sync/Memory
  if (!_decks || _decks.length === 0) _decks = getSyncDecks();
  if (_decks && _decks.length > 0) renderDecks();

  // 2. Load IndexedDB cache in background
  getCachedDecks().then(c => { if (c?.length) { _decks = c; persistDecksSync(c); renderDecks(); } }).catch(() => {});

  // 3. Network refresh (non-blocking)
  if (navigator.onLine) {
    try {
      await flushReviewOutbox();
      const res = await fetch('/api/anki/decks');
      if (res.ok) {
        const data = await res.json();
        if (data.status === 'ok' && Array.isArray(data.decks) && data.decks.length > 0) {
          _decks = data.decks;
          persistDecksSync(_decks);
          cacheDecks(_decks);
          renderDecks();
          ankiLog('DATA', 'DECK', 'DECKS_LOADED_FROM_API', { count: _decks.length });
          if (!_hasPrefetched || forcePrefetch) {
            _hasPrefetched = true;
            prefetchDeckCards(_decks);
          }
        }
      }
    } catch (err) {
      ankiLog('WARN', 'NET', 'DECKS_FETCH_FAILED_FALLBACK_CACHE', { error: String(err) });
    }
  }
}

export function updateSyncProgressBar(current, total, label = '') {
  const container = get('ankiSyncProgressBarContainer'), bar = get('ankiSyncProgressBar');
  const txtPercent = get('ankiSyncProgressPercent'), txtStatus = get('ankiSyncProgressStatus');
  if (!container || !bar) return;
  if (total <= 0 || current >= total) {
    if (bar) bar.style.width = '100%';
    if (txtPercent) txtPercent.innerText = '100%';
    if (txtStatus) txtStatus.innerHTML = '<span class="text-emerald-400 font-bold">✅ Sincronizzazione 100% pronta</span>';
    setTimeout(() => { if (container) container.classList.add('hidden'); }, 3000);
    return;
  }
  container.classList.remove('hidden');
  const pct = Math.max(2, Math.min(99, Math.round((current / total) * 100)));
  if (bar) bar.style.width = `${pct}%`;
  if (txtPercent) txtPercent.innerText = `${pct}%`;
  if (txtStatus) txtStatus.innerHTML = `<span class="animate-spin inline-block mr-1">🔄</span> ${label || 'Download...'} (${current}/${total})`;
}

export async function prefetchDeckCards(decks) {
  if (!decks || !Array.isArray(decks) || !navigator.onLine || _isPrefetching) return;
  _isPrefetching = true;
  const activeDecks = decks.filter(d => (d.total > 0) || d.is_master);
  const totalSteps = activeDecks.length;
  let done = 0;
  updateSyncProgressBar(0, totalSteps, 'Inizializzazione sincronizzazione');
  try {
    for (const d of activeDecks) {
      try {
        const cached = await getCachedDeckCards(d.id);
        if (cached?.fingerprint && d.fingerprint && cached.fingerprint === d.fingerprint && Array.isArray(cached.cards) && cached.cards.length > 0) {
          done++;
          updateSyncProgressBar(done, totalSteps, `Aggiornato ${d.display_name || d.name}`);
          continue;
        }
        const res = await fetch(`/api/anki/deck_cards?did=${d.id}&full=true`);
        if (res.ok) {
          const data = await res.json();
          if (data?.status === 'ok' && Array.isArray(data.cards)) {
            const fp = data.fingerprint || d.fingerprint || null;
            await cacheDeckCards(d.id, data.cards, data.counts || { new: 0, learning: 0, review: 0 }, fp);
            prefetchCardMedia(data.cards);
          }
        }
      } catch {}
      done++;
      updateSyncProgressBar(done, totalSteps, `Scaricamento ${d.display_name || d.name}`);
    }
    updateSyncProgressBar(totalSteps, totalSteps, 'Completato');
  } finally { _isPrefetching = false; }
}

let _lastRenderedFp = '';

export function toggleDeckCollapse(name) {
  if (_collapsedDecks.has(name)) _collapsedDecks.delete(name); else _collapsedDecks.add(name);
  saveCollapsedSet(_collapsedDecks); renderDecks(true);
}

export function toggleAllDecksCollapse(collapse) {
  if (collapse) _decks.filter(d => d.has_children).forEach(d => _collapsedDecks.add(d.name)); else _collapsedDecks.clear();
  saveCollapsedSet(_collapsedDecks); renderDecks(true);
}

function isDeckVisible(deck) {
  const parts = deck.name.split('::');
  let currentPath = '';
  for (let i = 0; i < parts.length - 1; i++) {
    currentPath = currentPath ? `${currentPath}::${parts[i]}` : parts[i];
    if (_collapsedDecks.has(currentPath)) return false;
  }
  return true;
}

export function renderDecks(force = false) {
  const container = get('ankiDecksContainer');
  if (!container) return;
  if (!_decks || _decks.length === 0) _decks = getSyncDecks();
  if (!_decks || _decks.length === 0) {
    container.innerHTML = `<div class="p-6 text-center text-neutral-400 font-mono text-xs">Nessun mazzo trovato.</div>`;
    _lastRenderedFp = ''; return;
  }
  const fp = _decks.map(d => `${d.id}:${d.new}:${d.learning}:${d.review}`).join('|') + ':' + _collapsedDecks.size;
  if (!force && fp === _lastRenderedFp) return;
  _lastRenderedFp = fp;
  const visibleDecks = _decks.filter(d => isDeckVisible(d));
  container.innerHTML = visibleDecks.map(d => renderDeckRow(d)).join('');
}

function renderDeckRow(d) {
  const totalDue = d.new + d.learning + d.review, escapedName = (d.display_name || d.name).replace(/'/g, "\'"), escapedRawName = d.name.replace(/'/g, "\'");
  const isCollapsed = _collapsedDecks.has(d.name), indentPx = d.level * 20 + 8, isParent = d.has_children || d.is_master;
  let chevronHtml = `<span class="w-6 h-6 flex items-center justify-center text-neutral-600 flex-shrink-0 text-xs">•</span>`;
  if (d.has_children) {
    chevronHtml = `<button type="button" onclick="event.stopPropagation(); window.ankiToggleDeckCollapse('${escapedRawName}')" class="w-6 h-6 flex items-center justify-center text-neutral-400 hover:text-white rounded hover:bg-white/10 flex-shrink-0 tap-press transition" title="${isCollapsed ? 'Espandi' : 'Comprimi'}"><svg class="w-3.5 h-3.5 transition-transform duration-150 ${isCollapsed ? '-rotate-90 text-neutral-500' : 'rotate-0 text-neutral-200'}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 9l-7 7-7-7"/></svg></button>`;
  }
  const deckTitle = d.level === 0 ? (d.display_name || d.name) : (d.leaf_name || d.name);
  const titleClass = isParent ? 'font-bold text-neutral-100 text-sm' : 'font-medium text-neutral-300 text-xs sm:text-sm';
  const rowBg = isParent && d.level === 0 ? 'bg-[#1C1C1C]' : 'bg-[#161616]';
  const gearSvg = `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>`;

  return `<div onclick="window.ankiOpenDeckOverview(${d.id}, '${escapedName}', ${d.new}, ${d.learning}, ${d.review})" style="padding-left: ${indentPx}px;" class="flex items-center justify-between pr-2 py-2.5 sm:py-3 ${rowBg} hover:bg-white/[0.04] active:bg-white/[0.08] cursor-pointer transition tap-press select-none group ${totalDue === 0 ? 'opacity-65' : ''}">
      <div class="flex items-center gap-1.5 min-w-0 pr-2">${chevronHtml}<span class="${titleClass} truncate group-hover:text-white" title="${d.name}">${deckTitle}</span></div>
      <div class="flex items-center font-mono text-xs sm:text-sm flex-shrink-0">
        <span class="w-11 sm:w-14 text-right ${d.new > 0 ? 'text-[#42A5F5] font-bold' : 'text-neutral-600'}">${d.new}</span>
        <span class="w-11 sm:w-14 text-right ${d.learning > 0 ? 'text-[#EF5350] font-bold' : 'text-neutral-600'}">${d.learning}</span>
        <span class="w-11 sm:w-14 text-right ${d.review > 0 ? 'text-[#66BB6A] font-bold' : 'text-neutral-600'}">${d.review}</span>
        <button type="button" onclick="event.stopPropagation(); window.ankiOpenDeckSettings(${d.id}, '${escapedName}')" class="p-1.5 text-neutral-500 hover:text-neutral-300 rounded hover:bg-white/10 ml-1 sm:ml-2 flex-shrink-0 tap-press" title="Impostazioni Mazzo">${gearSvg}</button>
      </div>
    </div>`;
}

export function openDeckOverview(did, name, newC = null, lrnC = null, revC = null) {
  stopCardTimer();
  const existing = _decks.find(d => Number(d.id) === Number(did));
  _selectedDeck = existing || { id: did, name, display_name: name, new: newC || 0, learning: lrnC || 0, review: revC || 0 };
  const dName = _selectedDeck.display_name || _selectedDeck.name;
  setCurrentDeck(_selectedDeck.id, dName); showView('overview');
  const setT = (id, v) => { const el = get(id); if (el) el.innerText = v; };
  setT('ankiAppTitle', 'Riepilogo Mazzo'); setT('ankiOverviewDeckName', dName);
  setT('ankiOverviewNew', _selectedDeck.new); setT('ankiOverviewLrn', _selectedDeck.learning); setT('ankiOverviewRev', _selectedDeck.review);
  get('ankiNavBackBtn')?.classList.remove('hidden'); get('ankiTopDuePill')?.classList.add('hidden');
  getCachedDeckCards(did).then(c => {
    if (c?.cards && _selectedDeck && Number(_selectedDeck.id) === Number(did)) {
      const lv = computeDeckCountsFromCards(c.cards);
      Object.assign(_selectedDeck, lv);
      setT('ankiOverviewNew', lv.new); setT('ankiOverviewLrn', lv.learning); setT('ankiOverviewRev', lv.review);
    }
  }).catch(() => {});
}
