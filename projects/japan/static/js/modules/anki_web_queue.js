// static/js/modules/anki_web_queue.js — Anki Learning Queue & Cooldown Scheduler
// Strictly <= 200 lines invariant.

import { renderLearningCooldownWaiting, renderSessionFinished } from './anki_web_study.js';
import { stopCardTimer } from './anki_web_timer.js';
import { ankiLog } from './anki_logger.js';

let _pendingLearning = [];
let _cooldownTimerId = null;

export function resetLearningQueue() {
  clearCooldownTimer();
  _pendingLearning = [];
}

export function clearCooldownTimer() {
  if (_cooldownTimerId) {
    clearInterval(_cooldownTimerId);
    _cooldownTimerId = null;
  }
}

export function enqueueFailedCard(card) {
  const isReviewLapse = (card.type === 2 || card.queue === 2);
  const cooldownSec = isReviewLapse ? 600 : 60;
  const req = {
    ...card,
    queue: 1,
    type: 1,
    ivl: 0,
    due_time: Date.now() + (cooldownSec * 1000),
    intervals: { again: '<10m', good: '1g' }
  };
  _pendingLearning.push(req);
  ankiLog('ACTION', 'SRS', 'ENQUEUE_LEARNING', { cid: card.id, cooldownSec });
  return req;
}

export function getPendingLearningCount() {
  return _pendingLearning.length;
}

export function getPendingLearningCards() {
  return _pendingLearning;
}

export function popDueLearningCard() {
  const now = Date.now();
  const idx = _pendingLearning.findIndex(c => c.due_time <= now);
  if (idx !== -1) {
    const [card] = _pendingLearning.splice(idx, 1);
    return card;
  }
  return null;
}

export function popEarliestLearningCard() {
  if (_pendingLearning.length === 0) return null;
  return _pendingLearning.shift();
}

export function advanceQueue(currentCards, currentIndex, onRenderCard, onFinish) {
  clearCooldownTimer();
  const now = Date.now();

  // 1. Red card with finished cooldown (RANDOM)
  const pendingReady = [];
  for (let i = 0; i < _pendingLearning.length; i++) {
    if (_pendingLearning[i].due_time <= now) pendingReady.push(i);
  }
  const currentRedReady = [];
  for (let i = currentIndex; i < currentCards.length; i++) {
    const c = currentCards[i];
    if (c && (c.queue === 1 || c.queue === 3)) {
      const dueMs = c.due_time || (c.due && c.due > 1000000000 ? c.due * 1000 : null);
      if (!dueMs || dueMs <= now) currentRedReady.push(i);
    }
  }

  const totalRedReady = pendingReady.length + currentRedReady.length;
  if (totalRedReady > 0) {
    const pick = Math.floor(Math.random() * totalRedReady);
    let card = null;
    if (pick < pendingReady.length) {
      const pIdx = pendingReady[pick];
      [card] = _pendingLearning.splice(pIdx, 1);
    } else {
      const cIdx = currentRedReady[pick - pendingReady.length];
      [card] = currentCards.splice(cIdx, 1);
    }
    currentCards.splice(currentIndex, 0, card);
    onRenderCard(currentIndex);
    return;
  }

  // 2. Green card with finished cooldown (RANDOM)
  const greenReady = [];
  for (let i = currentIndex; i < currentCards.length; i++) {
    const c = currentCards[i];
    if (c && c.queue === 2) {
      const dueMs = c.due_time || null;
      if (!dueMs || dueMs <= now) greenReady.push(i);
    }
  }
  if (greenReady.length > 0) {
    const gIdx = greenReady[Math.floor(Math.random() * greenReady.length)];
    const [card] = currentCards.splice(gIdx, 1);
    currentCards.splice(currentIndex, 0, card);
    onRenderCard(currentIndex);
    return;
  }

  // 3. Blue card (NOT random, in order)
  const bIdx = currentCards.findIndex((c, i) => i >= currentIndex && c && c.queue === 0);
  if (bIdx !== -1) {
    const [card] = currentCards.splice(bIdx, 1);
    currentCards.splice(currentIndex, 0, card);
    onRenderCard(currentIndex);
    return;
  }

  // 4. Red cards in future cooldown (waiting screen)
  const remainingFuture = [
    ..._pendingLearning,
    ...currentCards.slice(currentIndex).filter((c) => c && (c.queue === 1 || c.queue === 3))
  ];
  if (remainingFuture.length > 0) {
    startCooldownLoop(currentCards, currentIndex, onRenderCard, onFinish);
    return;
  }

  stopCardTimer();
  renderSessionFinished();
}

function startCooldownLoop(currentCards, currentIndex, onRenderCard, onFinish) {
  clearCooldownTimer();
  stopCardTimer();

  const update = () => {
    const now = Date.now();
    const hasReadyPending = _pendingLearning.some((c) => c.due_time <= now);
    const hasReadyCurrent = currentCards.slice(currentIndex).some((c) => {
      if (!c || (c.queue !== 1 && c.queue !== 3)) return false;
      const dueMs = c.due_time || (c.due && c.due > 1000000000 ? c.due * 1000 : null);
      return !dueMs || dueMs <= now;
    });

    if (hasReadyPending || hasReadyCurrent) {
      clearCooldownTimer();
      advanceQueue(currentCards, currentIndex, onRenderCard, onFinish);
      return;
    }

    const allFuture = [
      ..._pendingLearning,
      ...currentCards.slice(currentIndex).filter((c) => c && (c.queue === 1 || c.queue === 3))
    ];
    if (allFuture.length === 0) {
      clearCooldownTimer();
      renderSessionFinished();
      return;
    }

    const minDue = Math.min(...allFuture.map((c) => c.due_time || (now + 60000)));
    const remSec = Math.max(1, Math.ceil((minDue - now) / 1000));

    renderLearningCooldownWaiting(
      remSec,
      () => {
        clearCooldownTimer();
        let forced = null;
        if (_pendingLearning.length > 0) {
          forced = _pendingLearning.shift();
        } else {
          const rest = currentCards.splice(currentIndex, 1);
          forced = rest[0];
        }
        if (forced) {
          currentCards.splice(currentIndex, 0, forced);
          onRenderCard(currentIndex);
        } else {
          renderSessionFinished();
        }
      },
      () => {
        clearCooldownTimer();
        onFinish?.();
      }
    );
  };

  update();
  _cooldownTimerId = setInterval(update, 1000);
}
