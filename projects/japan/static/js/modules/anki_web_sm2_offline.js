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
      if (!c || c.queue < 0) continue;
      if (c.queue === 0) newC++;
      else if (c.queue === 1 || c.queue === 3) lrnC++;
      else if (c.queue === 2 && c.due <= td) revC++;
    }
  }
  return { new: newC, learning: lrnC, review: revC, total: cards?.length || 0 };
}

function shuffle(arr) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

export function filterDueCardsFromStore(cards, todayDays = null, limit = 0) {
  if (!Array.isArray(cards) || cards.length === 0) return [];
  const td = (todayDays !== null) ? todayDays : getOfflineTodayDays();
  const now = Date.now();
  const redReady = [], greenReady = [], blueNew = [], redFuture = [];

  for (let i = 0; i < cards.length; i++) {
    const c = cards[i];
    if (!c || c.queue < 0) continue;
    if (c.queue === 1 || c.queue === 3) {
      const dueMs = c.due_time || (c.due && c.due > 1000000000 ? c.due * 1000 : null);
      if (!dueMs || dueMs <= now) {
        redReady.push(c);
      } else {
        redFuture.push(c);
      }
    } else if (c.queue === 2 && c.due <= td) {
      greenReady.push(c);
    } else if (c.queue === 0) {
      blueNew.push(c);
    }
  }

  // User Invariant: Random red ready -> Random green ready -> Ordered blue new -> Future red
  shuffle(redReady);
  shuffle(greenReady);
  blueNew.sort((a, b) => ((a.due || 0) - (b.due || 0)) || ((a.id || 0) - (b.id || 0)));
  redFuture.sort((a, b) => ((a.due_time || 0) - (b.due_time || 0)));

  const result = [...redReady, ...greenReady, ...blueNew, ...redFuture];
  return (limit && limit > 0) ? result.slice(0, limit) : result;
}

export function calculateCardIntervals(card) {
  if (!card) return { again: '<10m', good: '1g' };
  if (card.queue === 0 || card.queue === 1 || card.queue === 3) {
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
