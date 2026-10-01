// static/js/modules/anki_web_ui.js — Controller & Event Coordinator for AnkiDroid Web
// Strictly <= 200 lines invariant.

import { cacheDeckCards, getCachedDeckCards, queueReview, flushReviewOutbox, clearCardCache, updateCachedCardReview } from './anki_web_db.js';
import { loadDecksListImpl, openDeckOverview, toggleDeckCollapse, toggleAllDecksCollapse } from './anki_web_decks.js';
import { speakJapanese, playAudio } from './anki_web_audio.js';
import { initCardTimer, getElapsedMs, startCardTimer, stopCardTimer, restartCardTimer, pauseCardTimer, setTimerDuration, applyTimerToAllDecks, getCardTimerDuration, setCurrentDeck as setTimerDeck } from './anki_web_timer.js';
import { initSessionTimer, startSessionTimer, pauseSessionTimer, setSessionTargetMin } from './anki_web_session_timer.js';
import { resetFatigueTracker, recordReviewForFatigue, hideFatigueModal, startMicroBreak, stopMicroBreak } from './anki_web_fatigue.js';
import { initCardSwipe, initCardKeybindings, animateCardEntrance, resetCardPosition, triggerProgrammaticSwipe } from './anki_web_gestures.js';
import { initAnkiSettings, setFrontFontSize, setBackFontSize, setFuriganaMode, resetFontSizes, toggleSettingsPanel } from './anki_web_settings.js';
import { initSettingsSync } from './anki_web_persistence.js';
import { applyUpdate } from './anki_web_updater.js';
import { ankiLog } from './anki_logger.js';
import { getSelectedDeck, setCurrentDeck, showView, updateCardElements, renderStudyHeader, renderSessionFinished, refreshCurrentCardView } from './anki_web_study.js';
import { resetLearningQueue, enqueueFailedCard, advanceQueue, clearCooldownTimer } from './anki_web_queue.js';
import { filterDueCardsFromStore, computeDeckCountsFromCards, getOfflineTodayDays } from './anki_web_sm2_offline.js';

let _currentCards = [], _currentIndex = 0, _isFlipped = false, _isAnswering = false;
let _history = [], _deckCounts = { new: 0, learning: 0, review: 0 }, _cardStartTime = 0, _sessionToken = 0;

const get = (id) => document.getElementById(id);

export async function initAnkiWeb() {
  ankiLog('ACTION', 'SYSTEM', 'INIT_ANKI_WEB', {});
  try { initAnkiSettings(); initSessionTimer(); initCardTimer(); } catch {}
  setupGestures();
  initSettingsSync(() => {
    try { initAnkiSettings(); initSessionTimer(); initCardTimer(); } catch {}
  }).catch(() => {});
  await loadDecksList();
}

export async function loadDecksList() {
  _sessionToken++; pauseSessionTimer(); clearCooldownTimer();
  try { await flushReviewOutbox(); } catch {}
  await loadDecksListImpl();
}

export function resetCurrentCardTimer() {
  _cardStartTime = Date.now();
  restartCardTimer();
  ankiLog('ACTION', 'CARD', 'TIMER_RESET', { cid: _currentCards[_currentIndex]?.id });
}

function setupGestures() {
  const cardEl = get('ankiCardContainer');
  initCardSwipe(
    cardEl, get('ankiBadgeWrong'), get('ankiBadgeCorrect'), get('ankiBadgeUndo'),
    () => _isFlipped && !_isAnswering, () => _history.length > 0 && !_isAnswering,
    (g) => answerCard(g), () => { if (!_isFlipped) flipCard(); }, () => undoReview(),
    () => resetCurrentCardTimer()
  );
  if (cardEl) cardEl.onclick = () => { if (!_isFlipped) flipCard(); };
  initCardKeybindings(() => _isFlipped && !_isAnswering, (g) => answerCard(g), () => { if (!_isFlipped) flipCard(); }, () => undoReview(), () => resetCurrentCardTimer());
}

export async function launchStudySession() {
  const deck = getSelectedDeck();
  if (!deck) return;
  const token = ++_sessionToken;
  _currentIndex = 0; _isFlipped = false; _history = []; _isAnswering = false; _currentCards = [];
  resetLearningQueue();
  const dName = deck.display_name || deck.name;
  setCurrentDeck(deck.id, dName); setTimerDeck(deck.id, dName);
  showView('study');
  if (get('ankiAppTitle')) get('ankiAppTitle').innerText = dName;
  get('ankiNavBackBtn')?.classList.remove('hidden');
  get('ankiTopDuePill')?.classList.remove('hidden');
  ankiLog('ACTION', 'DECK', 'LAUNCH_STUDY', { did: deck.id, name: deck.name, displayName: dName, token });
  startSessionTimer(); resetFatigueTracker();

  try { await flushReviewOutbox(); } catch {}
  let data = null;
  if (navigator.onLine) {
    try {
      const res = await fetch(`/api/anki/deck_cards?did=${deck.id}&t=${Date.now()}`);
      if (res.ok) {
        const json = await res.json();
        if (json?.status === 'ok' && Array.isArray(json.cards) && json.cards.length > 0) {
          data = json;
          cacheDeckCards(deck.id, data.cards, data.counts, json.fingerprint || deck.fingerprint);
          ankiLog('DATA', 'NET', 'CARDS_LOADED', { did: deck.id, count: data.cards.length });
        }
      }
    } catch (err) {
      ankiLog('WARN', 'CACHE', 'FALLBACK_CACHE', { did: deck.id, err: String(err) });
    }
  }

  if (!data?.cards?.length) {
    const cached = await getCachedDeckCards(deck.id);
    if (cached?.cards?.length) {
      const td = getOfflineTodayDays();
      const dueCards = filterDueCardsFromStore(cached.cards, td);
      data = { status: 'ok', cards: dueCards, counts: computeDeckCountsFromCards(cached.cards, td) };
      ankiLog('DATA', 'CACHE', 'LOADED_FROM_INDEXEDDB', { did: deck.id, count: dueCards.length, total: cached.cards.length });
    }
  }

  if (token !== _sessionToken) return;
  if (data?.status === 'ok' && data.cards?.length > 0) {
    _currentCards = data.cards; _deckCounts = data.counts || { new: 0, learning: 0, review: 0 };
    advanceQueue(_currentCards, _currentIndex, (idx) => { _currentIndex = idx; renderStudyCard(); }, () => loadDecksList());
  } else {
    stopCardTimer(); renderSessionFinished();
  }
}

export function flipCard() {
  if (_isFlipped || _isAnswering) return;
  _isFlipped = true; pauseCardTimer();
  const card = _currentCards[_currentIndex];
  if (card) {
    ankiLog('ACTION', 'CARD', 'CARD_FLIPPED', { cid: card.id, front: card.front?.substring(0, 30), deck: card.deck_name });
    updateCardElements(card, _isFlipped);
  }
}

export async function answerCard(grade) {
  if (_isAnswering) return;
  _isAnswering = true;
  const card = _currentCards[_currentIndex];
  if (!card) { _isAnswering = false; return; }
  const timeMs = Math.max(100, getElapsedMs() || (Date.now() - _cardStartTime)), dur = getCardTimerDuration(card);
  stopCardTimer(); setTimeout(() => recordReviewForFatigue(card, timeMs, grade, dur), 80);
  _history.push({ card, index: _currentIndex, counts: { ..._deckCounts } });
  ankiLog('ACTION', 'SRS', 'CARD_ANSWERED', { cid: card.id, grade, timeMs, queue: card.queue, deck: card.deck_name, front: card.front?.substring(0, 30) });

  const isLeech = (grade === 1 && (card.lapses || 0) >= 7), isNew = (card.queue === 0 || card.type === 0), isLrn = (card.queue === 1 || card.type === 1);
  if (isNew) _deckCounts.new = Math.max(0, _deckCounts.new - 1);
  else if (isLrn) _deckCounts.learning = Math.max(0, _deckCounts.learning - 1);
  else if (card.queue === 2) _deckCounts.review = Math.max(0, _deckCounts.review - 1);
  if (grade === 1) {
    if (isLeech) ankiLog('WARN', 'SRS', 'LEECH_QUARANTINED', { cid: card.id, lapses: (card.lapses || 0) + 1 });
    else { _deckCounts.learning = (_deckCounts.learning || 0) + 1; enqueueFailedCard(card); }
  }

  const payload = { card_id: card.id, grade, time_ms: timeMs, timestamp: Date.now() };
  updateCachedCardReview(card.did || (getSelectedDeck()?.id || 0), card.id, grade);
  if (!navigator.onLine) queueReview(payload);
  else fetch('/api/anki/review', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }).then(res => { if (!res.ok) queueReview(payload); }).catch(() => queueReview(payload));

  _currentIndex++; _isFlipped = false;
  advanceQueue(_currentCards, _currentIndex, (idx) => { _currentIndex = idx; renderStudyCard(true); }, () => loadDecksList());
  if (_currentIndex >= _currentCards.length - 2 && _currentCards.length >= 4) setTimeout(checkAndRefillCards, 150);
  _isAnswering = false;
}

let _isRefilling = false;
async function checkAndRefillCards() {
  if (_isRefilling) return;
  const deck = getSelectedDeck(), token = _sessionToken;
  if (!deck) return;
  _isRefilling = true;
  try {
    const rawCards = navigator.onLine
      ? (await (await fetch(`/api/anki/deck_cards?did=${deck.id}&t=${Date.now()}`)).json())?.cards
      : filterDueCardsFromStore((await getCachedDeckCards(deck.id))?.cards, getOfflineTodayDays());
    if (token !== _sessionToken || !Array.isArray(rawCards) || !rawCards.length) return;
    const existing = new Set(_currentCards.map(c => c.id));
    const fresh = rawCards.filter(c => !existing.has(c.id));
    if (fresh.length > 0) {
      _currentCards.push(...fresh);
      ankiLog('DATA', 'CACHE', 'REFILL_CARDS', { added: fresh.length, total: _currentCards.length });
    }
  } catch {} finally { _isRefilling = false; }
}

export function undoReview() {
  if (_history.length === 0) return;
  clearCooldownTimer();
  const last = _history.pop();
  _currentIndex = last.index; _deckCounts = last.counts; _isFlipped = false; _isAnswering = false;
  ankiLog('ACTION', 'SRS', 'UNDO_REVIEW', { cid: last.card?.id });
  renderStudyCard(true);
}

function renderStudyCard(animateIn = true) {
  const card = _currentCards[_currentIndex];
  if (!card) return;
  _cardStartTime = Date.now();
  renderStudyHeader(_deckCounts, _currentIndex + 1, _currentCards.length);
  updateCardElements(card, _isFlipped);
  ankiLog('DATA', 'CARD', 'CARD_RENDERED', { idx: _currentIndex, total: _currentCards.length, cid: card.id, deck: card.deck_name, front: card.front?.substring(0, 30) });
  if (animateIn) animateCardEntrance(); else resetCardPosition();
  if (!_isFlipped) startCardTimer(card);
}

function handleToggleSettings(f) { const c = _currentCards[_currentIndex]; if (c) setCurrentDeck(c.did || c.deck_id, c.deck_name); toggleSettingsPanel(f); } export async function hardReset() { ankiLog('ACTION', 'SYSTEM', 'HARD_RESET', {}); await applyUpdate(); }

Object.assign(window, {
  ankiShowDeckList: loadDecksList, ankiReloadDecks: hardReset, ankiHardReset: hardReset, ankiResetCardTimer: resetCurrentCardTimer, ankiOpenDeckOverview: openDeckOverview, ankiLaunchStudySession: launchStudySession, ankiToggleDeckCollapse: toggleDeckCollapse, ankiToggleAllCollapse: toggleAllDecksCollapse,
  ankiFlipCard: flipCard, ankiAnswerCard: answerCard, ankiTriggerSwipe: triggerProgrammaticSwipe, ankiUndo: undoReview, ankiUndoReview: undoReview, ankiSpeak: speakJapanese, ankiPlayAudio: playAudio, ankiToggleSettings: handleToggleSettings, ankiResetSettings: resetFontSizes, ankiSetFuriganaMode: setFuriganaMode,
  ankiSetFrontFontSize: setFrontFontSize, ankiSetBackFontSize: setBackFontSize, ankiSetTimerDuration: setTimerDuration, ankiApplyTimerToAllDecks: applyTimerToAllDecks, ankiRefreshCurrentCard: refreshCurrentCardView, ankiGetCurrentCard: () => _currentCards[_currentIndex],
  ankiOpenDeckSettings: (did, name) => { setCurrentDeck(did, name); setTimerDeck(did, name); if (window.ankiOpenCardTimerModal) window.ankiOpenCardTimerModal(did, name); }, ankiRenderTestCard: (c, f) => updateCardElements(c, f), ankiRenderSessionFinished: renderSessionFinished, ankiSetSessionTarget: setSessionTargetMin, ankiStartBreak: startMicroBreak, ankiStopBreak: stopMicroBreak, ankiDismissFatigue: hideFatigueModal
});
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initAnkiWeb); else initAnkiWeb();
