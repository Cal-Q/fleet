// static/js/modules/anki_deck_rollup.js — Client-Side Local Deck Counts & Rollup
// Strictly <= 200 lines, <= 100 cols invariant.

import { getDB } from './anki_web_db.js';
import {
  computeDeckCountsFromCards,
  getOfflineTodayDays
} from './anki_web_scheduler_offline.js';

export async function getAllCachedDeckRecords() {
  try {
    const db = await getDB();
    return new Promise((resolve) => {
      const tx = db.transaction('deck_cards', 'readonly');
      const req = tx.objectStore('deck_cards').getAll();
      req.onsuccess = () => resolve(Array.isArray(req.result) ? req.result : []);
      req.onerror = () => resolve([]);
    });
  } catch {
    return [];
  }
}

export function computeLocalRollupCounts(decks, cachedRecords, todayDays = null) {
  if (!Array.isArray(decks) || decks.length === 0) return decks;
  const td = (todayDays !== null) ? todayDays : getOfflineTodayDays();
  const leafMap = new Map();

  if (Array.isArray(cachedRecords)) {
    for (const rec of cachedRecords) {
      if (!rec || !rec.did || !Array.isArray(rec.cards)) continue;
      const c = computeDeckCountsFromCards(rec.cards, td);
      leafMap.set(Number(rec.did), c);
    }
  }

  // 1. First pass: update all leaf decks with locally computed counts
  for (const d of decks) {
    if (!d.has_children && !d.is_master) {
      const normDid = Number(d.id);
      if (leafMap.has(normDid)) {
        const c = leafMap.get(normDid);
        d.new = c.new;
        d.learning = c.learning;
        d.review = c.review;
        if (typeof c.total === 'number') d.total = c.total;
      }
    }
  }

  // 2. Second pass: rollup parent decks / raccolte from child leaf decks
  for (const d of decks) {
    if (d.has_children || d.is_master) {
      const prefix = `${d.name}::`;
      const children = decks.filter((c) =>
        !c.has_children && (c.name === d.name || c.name.startsWith(prefix))
      );
      if (children.length > 0) {
        d.new = children.reduce((sum, c) => sum + (c.new || 0), 0);
        d.learning = children.reduce((sum, c) => sum + (c.learning || 0), 0);
        d.review = children.reduce((sum, c) => sum + (c.review || 0), 0);
        d.total = children.reduce((sum, c) => sum + (c.total || 0), 0);
      }
    }
  }

  return decks;
}

export function getCardsForDeckLocal(deck, allDecks, cachedRecords) {
  if (!deck) return null;
  const normDid = Number(deck.id);
  const found = Array.isArray(allDecks)
    ? allDecks.find((d) => Number(d.id) === normDid)
    : null;
  const activeDeck = found ? {
    ...deck,
    ...found,
    display_name: deck.display_name || found.display_name || found.name,
    new: (deck.new !== undefined && deck.new !== null) ? deck.new : found.new,
    learning: (deck.learning !== undefined && deck.learning !== null)
      ? deck.learning : found.learning,
    review: (deck.review !== undefined && deck.review !== null) ? deck.review : found.review
  } : deck;

  const recMap = new Map();
  if (Array.isArray(cachedRecords)) {
    for (const rec of cachedRecords) {
      if (rec?.did) recMap.set(Number(rec.did), rec);
    }
  }

  if (!activeDeck.has_children && !activeDeck.is_master) {
    const rec = recMap.get(normDid);
    if (!rec || !Array.isArray(rec.cards)) return null;
    const counts = computeDeckCountsFromCards(rec.cards);
    return { did: normDid, cards: rec.cards, counts };
  }

  // For parent decks / raccolte: aggregate cards across all leaf descendants
  const prefix = `${activeDeck.name}::`;
  const childDecks = (Array.isArray(allDecks) ? allDecks : []).filter((c) =>
    !c.has_children && (c.name === activeDeck.name || c.name.startsWith(prefix))
  );

  const missingDueChild = childDecks.find((c) =>
    !recMap.has(Number(c.id)) && ((c.new || 0) + (c.learning || 0) + (c.review || 0) > 0)
  );
  if (missingDueChild) return null;

  const mergedCards = [];
  for (const child of childDecks) {
    const rec = recMap.get(Number(child.id));
    if (rec?.cards?.length) {
      mergedCards.push(...rec.cards);
    }
  }

  if (mergedCards.length === 0) return null;
  const counts = computeDeckCountsFromCards(mergedCards);
  return { did: normDid, cards: mergedCards, counts };
}
