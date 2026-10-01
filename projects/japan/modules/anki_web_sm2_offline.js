// static/js/modules/anki_web_sm2_offline.js — Authentic SM-2 Offline Engine & Dynamic Queue
// Strictly <= 200 lines invariant.

const ANKI_COL_CRT = 1734058800;

export function getOfflineTodayDays() {
  return Math.floor((Date.now() / 1000 - ANKI_COL_CRT) / 86400);
}

export function computeDeckCountsFromCards(cards, todayDays = null) {
  const td = (todayDays !== null) ? todayDays : getOfflineTodayDays();
  let newC = 0, lrnC = 0, revC = 0;
  if (Array.isArray(cards)) {
    for (let i = 0; i < cards.length; i++) {
      const c = cards[i];
      if (c.queue === 0 || c.type === 0) newC++;
      else if (c.queue === 1 || c.type === 1) lrnC++;
      else if (c.queue === 2 && (c.due <= td)) revC++;
    }
  }
  return { new: newC, learning: lrnC, review: revC, total: cards?.length || 0 };
}

export function filterDueCardsFromStore(cards, todayDays = null, limit = 0) {
  if (!Array.isArray(cards) || cards.length === 0) return [];
  const td = (todayDays !== null) ? todayDays : getOfflineTodayDays();
  const reviews = [], learning = [], newCards = [];

  for (let i = 0; i < cards.length; i++) {
    const c = cards[i];
    if (c.queue === 2 && (c.due <= td)) {
      reviews.push(c);
    } else if (c.queue === 1 || c.type === 1) {
      learning.push(c);
    } else if (c.queue === 0 || c.type === 0) {
      newCards.push(c);
    }
  }

  // Authentic SM-2 review order: Due reviews first, learning, then new cards
  const result = [...reviews, ...learning, ...newCards];
  return (limit && limit > 0) ? result.slice(0, limit) : result;
}

export function calculateCardIntervals(card) {
  if (!card) return { again: '<10m', good: '1g' };
  if (card.queue === 0 || card.type === 0 || card.queue === 1 || card.type === 1) {
    return { again: '<10m', good: '1g' };
  }
  const ivl = Math.max(1, card.ivl || 1);
  const factor = Math.max(1300, card.factor || 2500);
  const fMult = Math.max(1.3, factor / 1000.0);
  const nextGood = Math.max(1, Math.round(ivl * fMult));
  return { again: '<10m', good: `${nextGood}g` };
}

export function applySm2OfflineTransition(card, grade, todayDays = null) {
  const td = (todayDays !== null) ? todayDays : getOfflineTodayDays();
  const isReview = (card.queue === 2 || card.type === 2);

  if (isReview) {
    if (grade === 1) {
      card.lapses = (card.lapses || 0) + 1;
      card.factor = Math.max(1300, (card.factor || 2500) - 200);
      card.queue = 1;
      card.type = 1;
      card.due_time = Date.now() + 600000; // 10m relearning
      card.intervals = { again: '<10m', good: '1g' };
    } else {
      const fMult = Math.max(1.3, (card.factor || 2500) / 1000.0);
      const nextIvl = Math.max(1, Math.round((card.ivl || 1) * fMult));
      card.ivl = nextIvl;
      card.due = td + nextIvl;
      card.queue = 2;
      card.type = 2;
      card.reps = (card.reps || 0) + 1;
      delete card.due_time;
      card.intervals = calculateCardIntervals(card);
    }
  } else {
    // New or Learning card
    if (grade === 1) {
      card.queue = 1;
      card.type = 1;
      card.due_time = Date.now() + 60000; // 1m learning
      card.intervals = { again: '<10m', good: '1g' };
    } else {
      card.ivl = 1;
      card.due = td + 1; // Graduates to tomorrow
      card.queue = 2;
      card.type = 2;
      card.reps = (card.reps || 0) + 1;
      delete card.due_time;
      card.intervals = calculateCardIntervals(card);
    }
  }
  return card;
}
