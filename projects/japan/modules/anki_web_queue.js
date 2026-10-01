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
  const dueLearned = popDueLearningCard();
  if (dueLearned) {
    currentCards.splice(currentIndex, 0, dueLearned);
    onRenderCard(currentIndex);
    return;
  }

  while (currentIndex < currentCards.length) {
    const card = currentCards[currentIndex];
    if (!card.due_time || card.due_time <= Date.now()) {
      onRenderCard(currentIndex);
      return;
    }
    const readyIdx = currentCards.findIndex((c, i) => i > currentIndex && (!c.due_time || c.due_time <= Date.now()));
    if (readyIdx !== -1) {
      const [readyCard] = currentCards.splice(readyIdx, 1);
      currentCards.splice(currentIndex, 0, readyCard);
      onRenderCard(currentIndex);
      return;
    }
    break;
  }

  // Learn Ahead: when no other cards are ready in the queue, immediately serve the earliest learning card
  if (_pendingLearning.length > 0) {
    const learnAheadCard = popEarliestLearningCard();
    if (learnAheadCard) {
      currentCards.splice(currentIndex, 0, learnAheadCard);
      onRenderCard(currentIndex);
      return;
    }
  }

  if (currentIndex < currentCards.length) {
    // If cards remain in currentCards with future due_time, serve earliest immediately (Learn Ahead)
    const earlyCard = currentCards[currentIndex];
    onRenderCard(currentIndex);
    return;
  }

  stopCardTimer();
  renderSessionFinished();
}

function startCooldownLoop(onReadyCard, onExit) {
  clearCooldownTimer();
  if (_pendingLearning.length === 0) {
    renderSessionFinished();
    return;
  }

  const update = () => {
    const dueCard = popDueLearningCard();
    if (dueCard) {
      clearCooldownTimer();
      onReadyCard(dueCard);
      return;
    }

    if (_pendingLearning.length === 0) {
      clearCooldownTimer();
      renderSessionFinished();
      return;
    }

    const now = Date.now();
    const minDueTime = Math.min(..._pendingLearning.map(c => c.due_time || (now + 60000)));
    const remSec = Math.max(1, Math.ceil((minDueTime - now) / 1000));

    renderLearningCooldownWaiting(
      remSec,
      () => {
        clearCooldownTimer();
        const forced = popEarliestLearningCard();
        if (forced) onReadyCard(forced);
      },
      () => {
        clearCooldownTimer();
        if (onExit) onExit();
      }
    );
  };

  update();
  _cooldownTimerId = setInterval(update, 1000);
}
