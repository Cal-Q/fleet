// static/js/modules/anki_study_runner.js
// Active Study Card Queue & Review Loop Runner (<= 200 lines, <= 100 cols)
import { flushReviewOutbox } from './anki_web_db.js';
import {
  startCardTimer, stopCardTimer, restartCardTimer, pauseCardTimer,
  getElapsedMs, getCardTimerDuration
} from './anki_web_timer.js';
import { recordReviewForFatigue } from './anki_web_fatigue.js';
import { animateCardEntrance, resetCardPosition } from './anki_card_animator.js';
import { ankiLog } from './anki_logger.js';
import {
  getSelectedDeck, updateCardElements, renderStudyHeader, renderSessionFinished
} from './anki_web_study.js';
import {
  resetLearningQueue, advanceQueue, clearCooldownTimer, getPendingLearningCards
} from './anki_web_queue.js';
import {
  computeDeckCountsFromCards, getOfflineTodayDays
} from './anki_web_scheduler_offline.js';
import { flagCardForAltRule } from './anki_card_rule_hints.js';
import {
  fetchDeckStudyCards, fetchRefillCards, prepareStudySessionView
} from './anki_study_session.js';
import { handleCardGrading, syncCardReview } from './anki_web_reviewer.js';
import { prefetchCardMedia, preloadUpcomingCardImages } from './anki_web_media.js';

let _currentCards = [];
let _currentIndex = 0;
let _isFlipped = false;
let _isAnswering = false;
let _history = [];
let _cardStartTime = 0;
let _sessionToken = 0;
let _isRefilling = false;

export function computeCurrentSessionCounts() {
  const remaining = [
    ...getPendingLearningCards(),
    ..._currentCards.slice(_currentIndex)
  ];
  return computeDeckCountsFromCards(remaining, getOfflineTodayDays());
}

export const getCurrentCard = () => _currentCards[_currentIndex];
export const isCardFlipped = () => _isFlipped;
export const isAnswering = () => _isAnswering;
export const hasReviewHistory = () => _history.length > 0;
export const getDeckCounts = () => computeCurrentSessionCounts();
export const getSessionToken = () => _sessionToken;

export function resetCurrentCardTimer() {
  _cardStartTime = Date.now();
  restartCardTimer();
  ankiLog('ACTION', 'CARD', 'TIMER_RESET', { cid: _currentCards[_currentIndex]?.id });
}

export function triggerAltRuleAction(onSessionEnd) {
  if (_isAnswering) return;
  const card = _currentCards[_currentIndex];
  if (card) flagCardForAltRule(card);
  answerCard(1, onSessionEnd);
}

export function flipCard() {
  if (_isFlipped || _isAnswering) return;
  _isFlipped = true;
  pauseCardTimer();
  const card = _currentCards[_currentIndex];
  if (card) {
    ankiLog('ACTION', 'CARD', 'CARD_FLIPPED', { cid: card.id });
    updateCardElements(card, _isFlipped);
  }
}

export function unflipAndResetTimer() {
  if (_isAnswering) return;
  _isFlipped = false;
  const card = _currentCards[_currentIndex];
  if (card) {
    updateCardElements(card, false);
    resetCurrentCardTimer();
    ankiLog('ACTION', 'CARD', 'UNFLIP_AND_RESET_TIMER', { cid: card.id });
  }
}

export function undoReview() {
  if (_isFlipped) {
    unflipAndResetTimer();
    return;
  }
  if (_history.length === 0) return;
  clearCooldownTimer();
  const last = _history.pop();
  _currentIndex = last.index;
  _isFlipped = false;
  _isAnswering = false;
  ankiLog('ACTION', 'SRS', 'UNDO_REVIEW', { cid: last.card?.id });
  renderStudyCard(true);
}

export function renderStudyCard(animateIn = true) {
  const card = _currentCards[_currentIndex];
  if (!card) return;
  preloadUpcomingCardImages(_currentCards, _currentIndex, 4);
  _cardStartTime = Date.now();
  const counts = computeCurrentSessionCounts();
  renderStudyHeader(counts, _currentIndex + 1, _currentCards.length);
  updateCardElements(card, _isFlipped);
  ankiLog('DATA', 'CARD', 'CARD_RENDERED', { idx: _currentIndex, cid: card.id });
  const cardEl = document.getElementById('ankiCardContainer');
  if (animateIn) {
    animateCardEntrance(cardEl);
  } else {
    resetCardPosition(cardEl);
  }
  if (!_isFlipped) startCardTimer(card);
}

export async function launchStudySession(onSessionEnd) {
  const deck = getSelectedDeck();
  if (!deck) return;
  const token = ++_sessionToken;
  _currentIndex = 0;
  _isFlipped = false;
  _history = [];
  _isAnswering = false;
  _currentCards = [];
  resetLearningQueue();
  prepareStudySessionView(deck, token);
  try {
    await flushReviewOutbox();
  } catch {}
  const data = await fetchDeckStudyCards(deck);
  if (token !== _sessionToken) return;
  if (data?.status === 'ok' && data.cards?.length > 0) {
    _currentCards = data.cards;
    prefetchCardMedia(_currentCards);
    advanceQueue(_currentCards, _currentIndex, (idx) => {
      _currentIndex = idx;
      renderStudyCard();
    }, () => onSessionEnd?.());
  } else {
    stopCardTimer();
    renderSessionFinished();
  }
}

export async function answerCard(grade, onSessionEnd) {
  if (_isAnswering) return;
  _isAnswering = true;
  const card = _currentCards[_currentIndex];
  if (!card) {
    _isAnswering = false;
    return;
  }
  const timeMs = Math.max(100, getElapsedMs() || (Date.now() - _cardStartTime));
  const dur = getCardTimerDuration(card);
  stopCardTimer();
  setTimeout(() => recordReviewForFatigue(card, timeMs, grade, dur), 250);
  _history.push({ card, index: _currentIndex });
  ankiLog('ACTION', 'SRS', 'CARD_ANSWERED', { cid: card.id, grade, timeMs });

  handleCardGrading(card, grade);
  syncCardReview(card, grade, timeMs, getSelectedDeck()?.id);

  _currentIndex++;
  _isFlipped = false;
  advanceQueue(_currentCards, _currentIndex, (idx) => {
    _currentIndex = idx;
    renderStudyCard(true);
  }, () => onSessionEnd?.());
  if (_currentIndex >= _currentCards.length - 2 && _currentCards.length >= 4) {
    setTimeout(checkAndRefillCards, 150);
  }
  _isAnswering = false;
}

async function checkAndRefillCards() {
  if (_isRefilling) return;
  const deck = getSelectedDeck();
  const token = _sessionToken;
  if (!deck) return;
  _isRefilling = true;
  try {
    const fresh = await fetchRefillCards(deck, _currentCards);
    if (token === _sessionToken && fresh.length > 0) {
      _currentCards.push(...fresh);
      prefetchCardMedia(fresh);
      ankiLog('DATA', 'CACHE', 'REFILL_CARDS', { total: _currentCards.length });
    }
  } catch {} finally {
    _isRefilling = false;
  }
}
