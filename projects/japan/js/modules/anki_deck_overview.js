// static/js/modules/anki_deck_overview.js — Deck Overview Screen & Live Count Sync
// Strictly <= 200 lines, <= 100 cols invariant.

import { setCurrentDeck, showView } from './anki_web_study.js';
import { stopCardTimer } from './anki_web_timer.js';
import { getCachedDeckCards } from './anki_web_db.js';
import { prefetchCardMedia } from './anki_web_media.js';

const get = (id) => document.getElementById(id);

function setElementText(id, value) {
  const el = get(id);
  if (el) el.innerText = value;
}

export function openDeckOverview(decks, did, name, newC = null, lrnC = null, revC = null) {
  stopCardTimer();
  let targetDecks = decks;
  let targetDid = did;
  let targetName = name;
  let tNew = newC;
  let tLrn = lrnC;
  let tRev = revC;

  if (typeof decks === 'number' || (typeof decks === 'string' && !isNaN(Number(decks)))) {
    targetDid = Number(decks);
    targetName = did;
    tNew = name;
    tLrn = newC;
    tRev = lrnC;
    targetDecks = null;
  }

  const allAvailableDecks = Array.isArray(targetDecks) ? targetDecks : (
    (typeof window !== 'undefined' && Array.isArray(window.__INITIAL_DECKS__))
      ? window.__INITIAL_DECKS__ : []
  );
  const existing = allAvailableDecks.find((d) => Number(d.id) === Number(targetDid));
  const selectedDeck = existing ? { ...existing } : {
    id: Number(targetDid),
    name: targetName,
    display_name: targetName,
    new: tNew || 0,
    learning: tLrn || 0,
    review: tRev || 0
  };
  if (tNew !== null && tNew !== undefined) selectedDeck.new = tNew;
  if (tLrn !== null && tLrn !== undefined) selectedDeck.learning = tLrn;
  if (tRev !== null && tRev !== undefined) selectedDeck.review = tRev;

  const dName = selectedDeck.display_name || selectedDeck.name;
  setCurrentDeck(selectedDeck);
  showView('overview');

  setElementText('ankiAppTitle', 'Riepilogo Mazzo');
  setElementText('ankiOverviewDeckName', dName);
  setElementText('ankiOverviewNew', selectedDeck.new ?? 0);
  setElementText('ankiOverviewLrn', selectedDeck.learning ?? 0);
  setElementText('ankiOverviewRev', selectedDeck.review ?? 0);

  get('ankiNavBackBtn')?.classList.remove('hidden');
  get('ankiTopDuePill')?.classList.add('hidden');
  if (targetDid) {
    getCachedDeckCards(targetDid).then((c) => {
      if (c?.cards?.length) prefetchCardMedia(c.cards);
    }).catch(() => {});
  }
}
