// static/js/modules/anki_web_gestures.js
// Tactile Card Gestures & Input Event Coordinator (<= 200 lines, <= 100 cols)
import {
  setAnimatorBadges, renderDragVisualTransform,
  triggerFlyOff, triggerUndoFlyOff, triggerAltRuleFlyOff,
  animateCardEntrance as animCardEntrance,
  resetCardPosition as animResetCardPosition
} from './anki_card_animator.js';
export { initCardKeybindings } from './anki_web_keybindings.js';

let _isDragging = false;
let _startX = 0;
let _startY = 0;
let _currentX = 0;
let _currentY = 0;
let _activeCard = null;
let _rafId = null;

let _canSwipePredicate = null;
let _canUndoPredicate = null;
let _onSwipeCommit = null;
let _onTapCallback = null;
let _onUndoCallback = null;
let _onResetTimerCallback = null;
let _onAltRuleCallback = null;
let _getRemainingRatioFn = null;

const SWIPE_THRESHOLD = 75;

export function initCardSwipe(
  cardEl, wrongBadgeEl, correctBadgeEl, undoBadgeEl,
  canSwipe, canUndo, onSwipe, onTap, onUndo,
  onResetTimer = null, onAltRule = null, getRemainingRatio = null
) {
  if (!cardEl) return;
  _activeCard = cardEl;
  setAnimatorBadges({
    wrong: wrongBadgeEl,
    correct: correctBadgeEl,
    undo: undoBadgeEl || document.getElementById('ankiBadgeUndo'),
    reset: document.getElementById('ankiBadgeResetTimer'),
    altRule: document.getElementById('ankiBadgeAltRule')
  });
  _canSwipePredicate = canSwipe;
  _canUndoPredicate = canUndo;
  _onSwipeCommit = onSwipe;
  _onTapCallback = onTap;
  _onUndoCallback = onUndo;
  _onResetTimerCallback = onResetTimer;
  _onAltRuleCallback = onAltRule;
  _getRemainingRatioFn = getRemainingRatio;

  cardEl.removeEventListener('pointerdown', onPointerDown);
  cardEl.addEventListener('pointerdown', onPointerDown);
}

function onPointerDown(e) {
  if (e.target.closest('#ankiCardMeaningScroll')) return;
  const allowSwipe = typeof _canSwipePredicate === 'function' ? _canSwipePredicate() : true;
  if (allowSwipe) {
    if (!e.target.closest('#ankiCardSwipeZone')) return;
  } else {
    if (e.target.closest('button') || e.target.closest('a')) {
      return;
    }
  }

  _startX = e.clientX;
  _startY = e.clientY;
  _currentX = 0;
  _currentY = 0;
  _isDragging = true;
  if (_activeCard) {
    _activeCard.style.transition = 'none';
    _activeCard.setPointerCapture(e.pointerId);
  }
  window.addEventListener('pointermove', onPointerMove);
  window.addEventListener('pointerup', onPointerUp);
  window.addEventListener('pointercancel', onPointerUp);
}

function onPointerMove(e) {
  if (!_isDragging || !_activeCard) return;
  _currentX = e.clientX - _startX;
  _currentY = e.clientY - _startY;
  if (!_rafId) {
    _rafId = requestAnimationFrame(() => {
      _rafId = null;
      renderDragFrame();
    });
  }
}

function renderDragFrame() {
  if (!_isDragging || !_activeCard) return;
  const allowSwipe = typeof _canSwipePredicate === 'function' ? _canSwipePredicate() : true;
  const isFlipped = typeof _canSwipePredicate === 'function' ? _canSwipePredicate() : false;
  const rem = typeof _getRemainingRatioFn === 'function' ? _getRemainingRatioFn() : 1.0;
  const hasAlt = typeof _onAltRuleCallback === 'function';
  renderDragVisualTransform(
    _activeCard,
    _currentX,
    _currentY,
    allowSwipe,
    isFlipped,
    rem,
    hasAlt
  );
}

function handleSwipeDown(allowUndo) {
  const isFlipped = typeof _canSwipePredicate === 'function' ? _canSwipePredicate() : false;
  const rem = typeof _getRemainingRatioFn === 'function' ? _getRemainingRatioFn() : 1.0;

  if (isFlipped) {
    if (_onUndoCallback) _onUndoCallback();
    triggerVibrate();
    resetCardPosition();
  } else if (rem < 0.5 && _onResetTimerCallback) {
    _onResetTimerCallback();
    triggerVibrate();
    resetCardPosition();
  } else if (allowUndo) {
    triggerUndoFlyOff(_activeCard, _onUndoCallback);
  } else {
    resetCardPosition();
  }
}

function triggerVibrate() {
  if ('vibrate' in navigator) {
    try {
      navigator.vibrate([30, 20, 30]);
    } catch {}
  }
}

function onPointerUp(e) {
  const dist = Math.hypot(e.clientX - _startX, e.clientY - _startY);
  window.removeEventListener('pointermove', onPointerMove);
  window.removeEventListener('pointerup', onPointerUp);
  window.removeEventListener('pointercancel', onPointerUp);
  if (_rafId) {
    cancelAnimationFrame(_rafId);
    _rafId = null;
  }
  if (!_isDragging || !_activeCard) return;
  _isDragging = false;

  const allowSwipe = typeof _canSwipePredicate === 'function' ? _canSwipePredicate() : true;
  const allowUndo = typeof _canUndoPredicate === 'function' ? _canUndoPredicate() : true;

  if (dist < 12 && _onTapCallback) {
    _onTapCallback();
    resetCardPosition();
  } else if (_currentY > SWIPE_THRESHOLD && _currentY > Math.abs(_currentX) * 1.1) {
    handleSwipeDown(allowUndo);
  } else if (
    _currentY < -SWIPE_THRESHOLD &&
    Math.abs(_currentY) > Math.abs(_currentX) * 1.1 &&
    _onAltRuleCallback
  ) {
    triggerAltRuleFlyOff(_activeCard, _onAltRuleCallback);
  } else if (_currentX < -SWIPE_THRESHOLD && allowSwipe) {
    triggerFlyOff(_activeCard, -1, 1, _currentY, _onSwipeCommit);
  } else if (_currentX > SWIPE_THRESHOLD && allowSwipe) {
    triggerFlyOff(_activeCard, 1, 3, _currentY, _onSwipeCommit);
  } else {
    resetCardPosition();
  }
}

export function triggerProgrammaticSwipe(dir, grade) {
  if (typeof _canSwipePredicate === 'function' && !_canSwipePredicate()) return;
  const cardEl = _activeCard || document.getElementById('ankiCardContainer');
  if (cardEl) {
    const dirMult = dir === 'left' ? -1 : 1;
    triggerFlyOff(cardEl, dirMult, grade, 0, _onSwipeCommit);
  }
}

export function animateCardEntrance() {
  animCardEntrance(_activeCard || document.getElementById('ankiCardContainer'));
}

export function resetCardPosition() {
  animResetCardPosition(_activeCard || document.getElementById('ankiCardContainer'));
}
