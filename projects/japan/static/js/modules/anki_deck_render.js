// static/js/modules/anki_deck_render.js — Deck List DOM Rendering & Collapse State
// Strictly <= 200 lines, <= 100 cols invariant.

let _collapsedDecks = new Set();
let _lastRenderedFp = '';

const get = (id) => document.getElementById(id);

export function loadCollapsedSet() {
  try {
    const s = localStorage.getItem('anki_collapsed_decks');
    return s ? new Set(JSON.parse(s)) : new Set();
  } catch {
    return new Set();
  }
}

export function saveCollapsedSet(set) {
  try {
    localStorage.setItem('anki_collapsed_decks', JSON.stringify([...set]));
  } catch {}
}

_collapsedDecks = loadCollapsedSet();

export function toggleDeckCollapse(decks, name, onUpdate) {
  if (_collapsedDecks.has(name)) {
    _collapsedDecks.delete(name);
  } else {
    _collapsedDecks.add(name);
  }
  saveCollapsedSet(_collapsedDecks);
  if (onUpdate) onUpdate();
}

export function toggleAllDecksCollapse(decks, collapse, onUpdate) {
  if (collapse) {
    decks.filter((d) => d.has_children).forEach((d) => _collapsedDecks.add(d.name));
  } else {
    _collapsedDecks.clear();
  }
  saveCollapsedSet(_collapsedDecks);
  if (onUpdate) onUpdate();
}

export function isDeckVisible(deck) {
  const parts = deck.name.split('::');
  let currentPath = '';
  for (let i = 0; i < parts.length - 1; i++) {
    currentPath = currentPath ? `${currentPath}::${parts[i]}` : parts[i];
    if (_collapsedDecks.has(currentPath)) return false;
  }
  return true;
}

export function renderDecks(decks, force = false) {
  const container = get('ankiDecksContainer');
  if (!container) return;
  if (!decks || decks.length === 0) {
    container.innerHTML = `
      <div class="p-6 text-center text-neutral-400 font-mono text-xs">
        Nessun mazzo trovato.
      </div>
    `;
    _lastRenderedFp = '';
    return;
  }
  const countsStr = decks.map((d) => `${d.id}:${d.new}:${d.learning}:${d.review}`).join('|');
  const fp = `${countsStr}:${_collapsedDecks.size}`;
  if (!force && fp === _lastRenderedFp) return;
  _lastRenderedFp = fp;

  const visibleDecks = decks.filter((d) => isDeckVisible(d));
  container.innerHTML = visibleDecks.map((d) => renderDeckRow(d)).join('');
}

function renderChevron(d, isCollapsed, escapedRaw) {
  if (!d.has_children) {
    return `<span class="w-6 h-6 flex items-center justify-center ` +
      `text-neutral-600 flex-shrink-0 text-xs">•</span>`;
  }
  const rot = isCollapsed ? '-rotate-90 text-neutral-500' : 'rotate-0 text-neutral-200';
  const title = isCollapsed ? 'Espandi' : 'Comprimi';
  return `
    <button type="button"
      onclick="event.stopPropagation(); window.ankiToggleDeckCollapse('${escapedRaw}')"
      class="w-6 h-6 flex items-center justify-center text-neutral-400 ` +
      `hover:text-white rounded hover:bg-white/10 flex-shrink-0 tap-press transition"
      title="${title}">
      <svg class="w-3.5 h-3.5 transition-transform duration-150 ${rot}"
        fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5"
          d="M19 9l-7 7-7-7"/>
      </svg>
    </button>
  `;
}

function renderGearIcon() {
  return `
    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
        d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066` +
        `c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 ` +
        `1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37` +
        `a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 ` +
        `00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572` +
        `c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543` +
        `.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
    </svg>
  `;
}

function renderDeckRow(d) {
  const totalDue = d.new + d.learning + d.review;
  const escapedName = (d.display_name || d.name).replace(/'/g, "\\'");
  const escapedRaw = d.name.replace(/'/g, "\\'");
  const isCollapsed = _collapsedDecks.has(d.name);
  const indentPx = d.level * 20 + 8;
  const isParent = d.has_children || d.is_master;
  const chevron = renderChevron(d, isCollapsed, escapedRaw);
  const deckTitle = d.level === 0 ? (d.display_name || d.name) : (d.leaf_name || d.name);
  const titleClass = isParent
    ? 'font-bold text-neutral-100 text-sm'
    : 'font-medium text-neutral-300 text-xs sm:text-sm';
  const rowBg = isParent && d.level === 0 ? 'bg-[#1C1C1C]' : 'bg-[#161616]';
  const gearSvg = renderGearIcon();

  const newCls = d.new > 0 ? 'text-[#42A5F5] font-bold' : 'text-neutral-600';
  const lrnCls = d.learning > 0 ? 'text-[#EF5350] font-bold' : 'text-neutral-600';
  const revCls = d.review > 0 ? 'text-[#66BB6A] font-bold' : 'text-neutral-600';
  const opClass = totalDue === 0 ? 'opacity-65' : '';

  return `
    <div onclick="window.ankiOpenDeckOverview(${d.id}, '${escapedName}', ` +
      `${d.new}, ${d.learning}, ${d.review})"
      style="padding-left: ${indentPx}px;"
      class="flex items-center justify-between pr-2 py-2.5 sm:py-3 ${rowBg} ` +
      `hover:bg-white/[0.04] active:bg-white/[0.08] cursor-pointer transition ` +
      `tap-press select-none group ${opClass}">
      <div class="flex items-center gap-1.5 min-w-0 pr-2">
        ${chevron}
        <span class="${titleClass} truncate group-hover:text-white" title="${d.name}">
          ${deckTitle}
        </span>
      </div>
      <div class="flex items-center font-mono text-xs sm:text-sm flex-shrink-0">
        <span class="w-11 sm:w-14 text-right ${newCls}">${d.new}</span>
        <span class="w-11 sm:w-14 text-right ${lrnCls}">${d.learning}</span>
        <span class="w-11 sm:w-14 text-right ${revCls}">${d.review}</span>
        <button type="button"
          onclick="event.stopPropagation(); window.ankiOpenDeckSettings(${d.id}, '${escapedName}')"
          class="p-1.5 text-neutral-500 hover:text-neutral-300 rounded hover:bg-white/10 ` +
          `ml-1 sm:ml-2 flex-shrink-0 tap-press"
          title="Impostazioni Mazzo">
          ${gearSvg}
        </button>
      </div>
    </div>
  `;
}
