// static/js/modules/anki_card_animator.js
// Tactile Card Animation Physics & 60 FPS Visual Feedback (<= 200 lines, <= 100 cols)

let _badges = {};
let _backdropEl = null;
let _tintEl = null;
let _activeBadgeKey = null;
let _tintVisible = false;
let _currentColor = '';

const COLORS = {
  wrong: 'rgba(239, 83, 80, 0.35)',
  correct: 'rgba(102, 187, 106, 0.35)',
  undo: 'rgba(66, 165, 245, 0.35)',
  reset: 'rgba(255, 167, 38, 0.35)',
  altRule: 'rgba(245, 158, 11, 0.35)'
};

const getBackdrop = () =>
  _backdropEl || (_backdropEl = document.getElementById('ankiCardBackdrop'));

const getTint = () =>
  _tintEl || (_tintEl = document.getElementById('ankiCardTintOverlay'));

export function setAnimatorBadges(badges) {
  _badges = badges || {};
  _activeBadgeKey = null;
  _tintVisible = false;
  _currentColor = '';
}

export function resetVisualTints(force = false) {
  if (!force && !_activeBadgeKey && !_tintVisible) return;
  const badgeKeys = Object.keys(_badges);
  for (let i = 0; i < badgeKeys.length; i++) {
    const b = _badges[badgeKeys[i]];
    if (b) {
      b.style.transition = 'none';
      b.style.opacity = '0';
    }
  }
  _activeBadgeKey = null;
  const tint = getTint();
  if (tint) {
    tint.style.transition = 'none';
    tint.style.opacity = '0';
    _tintVisible = false;
  }
}

export function updateDragVisuals(type, p) {
  if (_activeBadgeKey && _activeBadgeKey !== type && _badges[_activeBadgeKey]) {
    _badges[_activeBadgeKey].style.opacity = '0';
  }
  if (_badges[type]) {
    _badges[type].style.opacity = String(p);
    _activeBadgeKey = type;
  }
  const tint = getTint();
  if (!tint) return;
  const col = COLORS[type];
  if (col && _currentColor !== col) {
    tint.style.backgroundColor = col;
    _currentColor = col;
  }
  tint.style.opacity = String(p);
  _tintVisible = p > 0.01;
}

export function updateBackdropDrag() {
  const backdrop = getBackdrop();
  if (!backdrop) return;
  backdrop.style.transform = 'translate3d(0, 8px, 0) scale(0.94)';
}

export function resetBackdropPosition() {
  const backdrop = getBackdrop();
  if (!backdrop) return;
  backdrop.style.transition =
    'transform 0.20s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
  backdrop.style.transform = 'translate3d(0, 8px, 0) scale(0.94)';
}

export function animateBackdropForward() {
  const backdrop = getBackdrop();
  if (!backdrop) return;
  backdrop.style.transition =
    'transform 0.20s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.18s ease-out';
  backdrop.style.transform = 'translate3d(0, 0, 0) scale(1.0)';
  backdrop.style.opacity = '1.0';
}

export function animateFlyOff(cardEl, trans, badge, cb) {
  const el = cardEl || document.getElementById('ankiCardContainer');
  if (!el) {
    if (typeof cb === 'function') cb();
    return;
  }
  el.style.transition =
    'transform 0.28s cubic-bezier(0.25, 1, 0.5, 1), opacity 0.24s ease-in';
  el.style.transform = trans;
  el.style.opacity = '0';
  updateDragVisuals(badge, 1);
  setTimeout(() => {
    animateBackdropForward();
  }, 160);
  setTimeout(() => {
    resetVisualTints(true);
    if (typeof cb === 'function') {
      cb();
    }
  }, 360);
}

export function triggerFlyOff(cardEl, dirMultiplier, grade, curY, onCommit) {
  const trans =
    `translate3d(${dirMultiplier * 130}vw, ${curY}px, 0) rotate(${dirMultiplier * 25}deg)`;
  const badge = dirMultiplier < 0 ? 'wrong' : 'correct';
  animateFlyOff(cardEl, trans, badge, () => {
    if (typeof onCommit === 'function') {
      onCommit(grade);
    }
  });
}

export function triggerUndoFlyOff(cardEl, onUndo) {
  animateFlyOff(cardEl, 'translate3d(0, 130vh, 0) scale(0.85)', 'undo', onUndo);
}

export function triggerAltRuleFlyOff(cardEl, onAltRule) {
  animateFlyOff(cardEl, 'translate3d(0, -130vh, 0) scale(0.85)', 'altRule', onAltRule);
}

export function animateCardEntrance(cardEl) {
  const el = cardEl || document.getElementById('ankiCardContainer');
  if (!el) return;
  resetVisualTints(true);
  el.style.transition = 'none';
  el.style.transform = 'translate3d(0, 0, 0) scale(1)';
  el.style.opacity = '0';
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      el.style.transition = 'opacity 0.20s ease-out';
      el.style.opacity = '1';
      setTimeout(() => {
        const b = getBackdrop();
        if (b) {
          b.style.transition = 'none';
          b.style.transform = 'translate3d(0, 8px, 0) scale(0.94)';
          b.style.opacity = '0.80';
        }
      }, 200);
    });
  });
}

export function resetCardPosition(cardEl) {
  const el = cardEl || document.getElementById('ankiCardContainer');
  if (!el) return;
  el.style.transition =
    'transform 0.20s cubic-bezier(0.175, 0.885, 0.32, 1.275), opacity 0.18s ease-out';
  el.style.transform = 'translate3d(0, 0, 0) scale(1) rotate(0deg)';
  el.style.opacity = '1';
  resetBackdropPosition();
  resetVisualTints(true);
}

export function renderDragVisualTransform(
  cardEl, curX, curY, allowSwipe, isFlipped, rem, hasAlt
) {
  if (!cardEl) return;
  updateBackdropDrag(curX, curY);
  const isH = Math.abs(curX) >= Math.abs(curY);
  const threshold = 75;
  if (isH && allowSwipe) {
    cardEl.style.transform =
      `translate3d(${curX}px, ${curY * 0.3}px, 0) rotate(${curX * 0.05}deg)`;
    const badgeType = curX < 0 ? 'wrong' : 'correct';
    updateDragVisuals(badgeType, Math.min(1, Math.abs(curX) / threshold));
  } else if (!isH && curY > 0) {
    const p = Math.min(1, curY / threshold);
    const scale = Math.max(0.92, 1 - curY * 0.0006);
    cardEl.style.transform = `translate3d(${curX * 0.25}px, ${curY}px, 0) scale(${scale})`;
    const badge = isFlipped ? 'undo' : (rem < 0.5 ? 'reset' : 'undo');
    updateDragVisuals(badge, p);
  } else if (!isH && curY < 0 && hasAlt) {
    const p = Math.min(1, Math.abs(curY) / threshold);
    const scale = Math.max(0.92, 1 - Math.abs(curY) * 0.0006);
    cardEl.style.transform = `translate3d(${curX * 0.2}px, ${curY}px, 0) scale(${scale})`;
    updateDragVisuals('altRule', p);
  } else {
    cardEl.style.transform = `translate3d(${curX * 0.2}px, ${curY * 0.2}px, 0)`;
    resetVisualTints();
  }
}
