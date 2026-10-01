// static/js/modules/anki_study_session.js
// Session Card Fetching & Background Refill Coordinator (<= 200 lines, <= 100 cols)

import { cacheDeckCards } from './anki_web_db.js';
import {
  filterDueCardsFromStore, computeDeckCountsFromCards, getOfflineTodayDays
} from './anki_web_scheduler_offline.js';
import { ankiLog } from './anki_logger.js';
import { setCurrentDeck, showView, renderStudyHeader } from './anki_web_study.js';
import { setCurrentDeck as setTimerDeck } from './anki_web_timer.js';
import { startSessionTimer } from './anki_web_session_timer.js';
import { resetFatigueTracker } from './anki_web_fatigue.js';
import {
  getAllCachedDeckRecords, getCardsForDeckLocal
} from './anki_deck_rollup.js';
import { getDecksList } from './anki_web_decks.js';

export function prepareStudySessionView(deck, token) {
  const dName = deck.display_name || deck.name;
  setCurrentDeck(deck);
  setTimerDeck(deck.id, dName);
  showView('study');
  const appTitle = document.getElementById('ankiAppTitle');
  if (appTitle) appTitle.innerText = dName;
  document.getElementById('ankiNavBackBtn')?.classList.remove('hidden');
  document.getElementById('ankiTopDuePill')?.classList.remove('hidden');
  const cardCont = document.getElementById('ankiCardContainer');
  if (cardCont) {
    cardCont.style.transition = 'none';
    cardCont.style.transform = 'translate3d(0, 0, 0) scale(1) rotate(0deg)';
    cardCont.style.opacity = '1';
  }
  const backdrop = document.getElementById('ankiCardBackdrop');
  if (backdrop) {
    backdrop.style.transition = 'none';
    backdrop.style.transform = 'translate3d(0, 8px, 0) scale(0.94)';
    backdrop.style.opacity = '0.80';
  }
  renderStudyHeader(deck);
  ankiLog('ACTION', 'DECK', 'LAUNCH_STUDY', {
    did: deck.id,
    name: deck.name,
    displayName: dName,
    token
  });
  startSessionTimer();
  resetFatigueTracker();
}

export async function fetchDeckStudyCards(deck) {
  const allRecords = await getAllCachedDeckRecords();
  const cached = getCardsForDeckLocal(deck, getDecksList(), allRecords);
  if (cached?.cards?.length) {
    const td = getOfflineTodayDays();
    const dueCards = filterDueCardsFromStore(cached.cards, td);
    if (dueCards.length > 0) {
      ankiLog('DATA', 'CACHE', 'LOADED_FROM_INDEXEDDB', {
        did: deck.id,
        count: dueCards.length,
        total: cached.cards.length
      });
      return {
        status: 'ok',
        cards: dueCards,
        counts: computeDeckCountsFromCards(cached.cards, td)
      };
    }
  }

  if (navigator.onLine) {
    try {
      const res = await fetch(`/api/anki/deck_cards?did=${deck.id}&t=${Date.now()}`);
      if (res.ok) {
        const json = await res.json();
        if (json?.status === 'ok' && Array.isArray(json.cards)) {
          cacheDeckCards(deck.id, json.cards, json.counts, json.fingerprint || deck.fingerprint);
          const byDid = new Map();
          for (const c of json.cards) {
            if (!c.did) continue;
            if (!byDid.has(c.did)) byDid.set(c.did, []);
            byDid.get(c.did).push(c);
          }
          if (byDid.size > 1 || (byDid.size === 1 && !byDid.has(deck.id))) {
            const td = getOfflineTodayDays();
            for (const [cDid, cList] of byDid.entries()) {
              const cCounts = computeDeckCountsFromCards(cList, td);
              cacheDeckCards(cDid, cList, cCounts, null);
            }
          }
          ankiLog('DATA', 'NET', 'CARDS_LOADED', { did: deck.id, count: json.cards.length });
          return json;
        }
      }
    } catch (err) {
      ankiLog('WARN', 'CACHE', 'FALLBACK_CACHE', { did: deck.id, err: String(err) });
    }
  }

  if (cached?.cards?.length) {
    const td = getOfflineTodayDays();
    const dueCards = filterDueCardsFromStore(cached.cards, td);
    return {
      status: 'ok',
      cards: dueCards,
      counts: computeDeckCountsFromCards(cached.cards, td)
    };
  }
  return null;
}
