// static/js/modules/anki_web_gestures.js — Tactile Card Swipe Physics & Stack Animation
// Strictly <= 200 lines invariant.

let _isDragging = false, _startX = 0, _startY = 0, _currentX = 0, _currentY = 0;
let _activeCard = null, _wrongBadge = null, _correctBadge = null, _undoBadge = null, _resetBadge = null;
let _canSwipePredicate = null, _canUndoPredicate = null;
let _onSwipeCommit = null, _onTapCallback = null, _onUndoCallback = null, _onResetTimerCallback = null;

const SWIPE_THRESHOLD = 75;

export function initCardSwipe(cardEl, wrongBadgeEl, correctBadgeEl, undoBadgeEl, canSwipe, canUndo, onSwipe, onTap, onUndo, onResetTimer = null) {
  if (!cardEl) return;
  _activeCard = cardEl; _wrongBadge = wrongBadgeEl; _correctBadge = correctBadgeEl;
  _undoBadge = undoBadgeEl || document.getElementById('ankiBadgeUndo');
  _resetBadge = document.getElementById('ankiBadgeResetTimer');
  _canSwipePredicate = canSwipe; _canUndoPredicate = canUndo;
  _onSwipeCommit = onSwipe; _onTapCallback = onTap; _onUndoCallback = onUndo; _onResetTimerCallback = onResetTimer;
  cardEl.removeEventListener('pointerdown', onPointerDown);
  cardEl.addEventListener('pointerdown', onPointerDown);

  const scrollEl = document.getElementById('ankiCardMeaningScroll');
  if (scrollEl) {
    const stopProp = (e) => e.stopPropagation();
    ['pointerdown', 'touchstart', 'touchmove', 'wheel'].forEach(evt => scrollEl.addEventListener(evt, stopProp, { passive: evt !== 'pointerdown' }));
  }
}

function onPointerDown(e) {
  const allowSwipe = typeof _canSwipePredicate === 'function' ? _canSwipePredicate() : true;
  if (allowSwipe) {
    if (!e.target.closest('#ankiCardSwipeZone')) return;
  } else {
    if (e.target.closest('button') || e.target.closest('a') || e.target.closest('#ankiCardMeaningScroll')) return;
  }

  _startX = e.clientX; _startY = e.clientY;
  _currentX = 0; _currentY = 0;
  _isDragging = true;
  if (_activeCard) {
    _activeCard.style.transition = 'none';
    _activeCard.setPointerCapture(e.pointerId);
  }
  window.addEventListener('pointermove', onPointerMove);
  window.addEventListener('pointerup', onPointerUp);
  window.addEventListener('pointercancel', onPointerUp);
}

let _rafId = null;

function updateDragVisuals(type, p) {
  const tint = document.getElementById('ankiCardTintOverlay');
  if (_wrongBadge) { _wrongBadge.style.transition = 'none'; _wrongBadge.style.opacity = type === 'wrong' ? p : 0; }
  if (_correctBadge) { _correctBadge.style.transition = 'none'; _correctBadge.style.opacity = type === 'correct' ? p : 0; }
  if (_undoBadge) { _undoBadge.style.transition = 'none'; _undoBadge.style.opacity = type === 'undo' ? p : 0; }
  if (_resetBadge) { _resetBadge.style.transition = 'none'; _resetBadge.style.opacity = type === 'reset' ? p : 0; }
  const col = type === 'wrong' ? '239, 83, 80' : type === 'correct' ? '102, 187, 106' : type === 'undo' ? '66, 165, 245' : '255, 167, 38';
  if (tint) { tint.style.transition = 'none'; tint.style.backgroundColor = `rgba(${col}, 0.35)`; tint.style.opacity = String(p); }
}

function renderDragFrame() {
  if (!_isDragging || !_activeCard) return;
  const isHorizontal = Math.abs(_currentX) >= Math.abs(_currentY);
  const allowSwipe = typeof _canSwipePredicate === 'function' ? _canSwipePredicate() : true;
  const allowUndo = typeof _canUndoPredicate === 'function' ? _canUndoPredicate() : true;

  if (isHorizontal && allowSwipe) {
    const rot = _currentX * 0.05;
    _activeCard.style.transform = `translate3d(${_currentX}px, ${_currentY * 0.3}px, 0) rotate(${rot}deg)`;
    if (_currentX < 0) updateDragVisuals('wrong', Math.min(1, Math.abs(_currentX) / SWIPE_THRESHOLD));
    else if (_currentX > 0) updateDragVisuals('correct', Math.min(1, _currentX / SWIPE_THRESHOLD));
  } else if (!isHorizontal && _currentY > 0 && allowUndo) {
    const p = Math.min(1, _currentY / SWIPE_THRESHOLD), scale = Math.max(0.92, 1 - _currentY * 0.0006);
    _activeCard.style.transform = `translate3d(${_currentX * 0.25}px, ${_currentY}px, 0) scale(${scale})`;
    updateDragVisuals('undo', p);
  } else if (!isHorizontal && _currentY < 0 && typeof _onResetTimerCallback === 'function') {
    const p = Math.min(1, Math.abs(_currentY) / 50), scale = Math.max(0.94, 1 - Math.abs(_currentY) * 0.0005);
    _activeCard.style.transform = `translate3d(${_currentX * 0.2}px, ${_currentY}px, 0) scale(${scale})`;
    updateDragVisuals('reset', p);
  } else {
    _activeCard.style.transform = `translate3d(${_currentX * 0.2}px, ${_currentY * 0.2}px, 0)`;
    resetVisualTints();
  }
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

function onPointerUp(e) {
  const dist = Math.hypot(e.clientX - _startX, e.clientY - _startY);
  window.removeEventListener('pointermove', onPointerMove);
  window.removeEventListener('pointerup', onPointerUp);
  window.removeEventListener('pointercancel', onPointerUp);
  if (_rafId) { cancelAnimationFrame(_rafId); _rafId = null; }
  if (!_isDragging || !_activeCard) return;
  _isDragging = false;

  const allowSwipe = typeof _canSwipePredicate === 'function' ? _canSwipePredicate() : true;
  const allowUndo = typeof _canUndoPredicate === 'function' ? _canUndoPredicate() : true;

  if (dist < 12 && typeof _onTapCallback === 'function') {
    _onTapCallback();
    resetCardPosition();
  } else if (_currentY > SWIPE_THRESHOLD && _currentY > Math.abs(_currentX) * 1.1 && allowUndo) {
    triggerUndoFlyOff();
  } else if (_currentY < -48 && Math.abs(_currentY) > Math.abs(_currentX) * 1.1 && typeof _onResetTimerCallback === 'function') {
    triggerResetTimerAction();
  } else if (_currentX < -SWIPE_THRESHOLD && allowSwipe) {
    triggerFlyOff(-1, 1);
  } else if (_currentX > SWIPE_THRESHOLD && allowSwipe) {
    triggerFlyOff(1, 3);
  } else {
    resetCardPosition();
  }
}

export function triggerProgrammaticSwipe(direction, grade) {
  if (_activeCard) triggerFlyOff(direction === 'left' ? -1 : 1, grade);
}

function triggerFlyOff(dirMultiplier, grade) {
  if (!_activeCard) return;
  _activeCard.style.transition = 'transform 0.22s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.18s ease-out';
  _activeCard.style.transform = `translate3d(${dirMultiplier * 130}vw, ${_currentY}px, 0) rotate(${dirMultiplier * 25}deg)`;
  _activeCard.style.opacity = '0';
  updateDragVisuals(dirMultiplier < 0 ? 'wrong' : 'correct', 1);
  setTimeout(() => { resetVisualTints(); if (typeof _onSwipeCommit === 'function') _onSwipeCommit(grade); }, 190);
}

export function triggerUndoFlyOff() {
  if (!_activeCard) return;
  _activeCard.style.transition = 'transform 0.22s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.18s ease-out';
  _activeCard.style.transform = 'translate3d(0, 130vh, 0) scale(0.85)';
  _activeCard.style.opacity = '0';
  updateDragVisuals('undo', 1);
  setTimeout(() => { resetVisualTints(); if (typeof _onUndoCallback === 'function') _onUndoCallback(); }, 180);
}

function triggerResetTimerAction() {
  if (typeof _onResetTimerCallback === 'function') _onResetTimerCallback();
  if ('vibrate' in navigator) try { navigator.vibrate([30, 20, 30]); } catch {}
  resetCardPosition();
}

function resetVisualTints() {
  [_wrongBadge, _correctBadge, _undoBadge, _resetBadge].forEach(b => { if (b) { b.style.transition = 'none'; b.style.opacity = '0'; } });
  const tint = document.getElementById('ankiCardTintOverlay');
  if (tint) { tint.style.transition = 'none'; tint.style.opacity = '0'; }
}

export function animateCardEntrance() {
  if (!_activeCard) return;
  resetVisualTints();
  _activeCard.style.transition = 'none';
  _activeCard.style.transform = 'translate3d(0, 10px, 0) scale(0.96)';
  _activeCard.style.opacity = '0';
  requestAnimationFrame(() => requestAnimationFrame(() => {
    if (!_activeCard) return;
    _activeCard.style.transition = 'transform 0.22s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.18s ease-out';
    _activeCard.style.transform = 'translate3d(0, 0, 0) scale(1) rotate(0deg)';
    _activeCard.style.opacity = '1';
  }));
}

export function resetCardPosition() {
  if (!_activeCard) return;
  _activeCard.style.transition = 'transform 0.22s cubic-bezier(0.175, 0.885, 0.32, 1.275), opacity 0.18s ease-out';
  _activeCard.style.transform = 'translate3d(0, 0, 0) scale(1) rotate(0deg)';
  _activeCard.style.opacity = '1';
  resetVisualTints();
}

export function initCardKeybindings(isFlippedFn, onSwipeFn, onFlipFn, onUndoFn, onResetTimerFn = null) {
  window.addEventListener('keydown', (e) => {
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName) || document.activeElement?.isContentEditable) return;
    const sView = document.getElementById('ankiStudyView');
    if (!sView || sView.classList.contains('hidden')) return;
    if (e.key === 'z' || (e.key === 'z' && (e.ctrlKey || e.metaKey))) { e.preventDefault(); onUndoFn(); return; }
    if ((e.key === 'r' || e.key === 'R' || e.key === 'ArrowUp') && typeof onResetTimerFn === 'function') {
      e.preventDefault(); onResetTimerFn(); return;
    }
    const flipped = typeof isFlippedFn === 'function' ? isFlippedFn() : false;
    if (e.code === 'Space' || e.key === 'Enter') {
      e.preventDefault();
      if (!flipped) onFlipFn(); else triggerProgrammaticSwipe('right', 3);
    } else if (flipped) {
      if (e.key === '1' || e.key === 'ArrowLeft') { e.preventDefault(); triggerProgrammaticSwipe('left', 1); }
      if (e.key === '2' || e.key === 'ArrowRight') { e.preventDefault(); triggerProgrammaticSwipe('right', 3); }
    }
  });
}
