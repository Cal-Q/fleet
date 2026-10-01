// static/js/modules/anki_card_animator.js
// Tactile Card Animation Physics & Visual Feedback (<= 200 lines, <= 100 cols)

let _badges = {};

const getBackdrop = () => document.getElementById('ankiCardBackdrop');

export function setAnimatorBadges(badges) {
  _badges = badges || {};
}

export function resetVisualTints() {
  const badgeKeys = Object.keys(_badges);
  for (let i = 0; i < badgeKeys.length; i++) {
    const el = _badges[badgeKeys[i]];
    if (el) {
      el.style.transition = 'none';
      el.style.opacity = '0';
    }
  }
  const badges = document.querySelectorAll('.stamp-badge');
  for (let i = 0; i < badges.length; i++) {
    badges[i].style.transition = 'none';
    badges[i].style.opacity = '0';
  }
  const tint = document.getElementById('ankiCardTintOverlay');
  if (tint) {
    tint.style.transition = 'none';
    tint.style.opacity = '0';
  }
}

export function updateDragVisuals(type, p) {
  const badgeKeys = Object.keys(_badges);
  for (let i = 0; i < badgeKeys.length; i++) {
    const k = badgeKeys[i];
    const el = _badges[k];
    if (el) {
      el.style.transition = 'none';
      el.style.opacity = (k === type ? String(p) : '0');
    }
  }
  const tint = document.getElementById('ankiCardTintOverlay');
  if (!tint) return;
  const colors = {
    wrong: '239, 83, 80',
    correct: '102, 187, 106',
    undo: '66, 165, 245',
    reset: '255, 167, 38',
    altRule: '245, 158, 11'
  };
  const rgb = colors[type] || '255, 255, 255';
  tint.style.transition = 'none';
  tint.style.backgroundColor = `rgba(${rgb}, 0.35)`;
  tint.style.opacity = String(p);
}

export function updateBackdropDrag(curX, curY) {
  const backdrop = getBackdrop();
  if (!backdrop) return;
  const dist = Math.hypot(curX, curY);
  const p = Math.min(1, dist / 110);
  const scale = (0.94 + 0.06 * p).toFixed(3);
  const y = Math.round(8 * (1 - p));
  const op = (0.70 + 0.30 * p).toFixed(2);
  backdrop.style.transition = 'none';
  backdrop.style.transform = `translate3d(0, ${y}px, 0) scale(${scale})`;
  backdrop.style.opacity = op;
}

export function resetBackdropPosition() {
  const backdrop = getBackdrop();
  if (!backdrop) return;
  backdrop.style.transition =
    'transform 0.22s cubic-bezier(0.175, 0.885, 0.32, 1.275), opacity 0.18s ease-out';
  backdrop.style.transform = 'translate3d(0, 8px, 0) scale(0.94)';
  backdrop.style.opacity = '0.70';
}

export function animateBackdropForward() {
  const backdrop = getBackdrop();
  if (!backdrop) return;
  backdrop.style.transition =
    'transform 0.12s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.10s ease-out';
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
    'transform 0.10s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.08s ease-out';
  el.style.transform = trans;
  el.style.opacity = '0';
  updateDragVisuals(badge, 1);
  animateBackdropForward();
  setTimeout(() => {
    resetVisualTints();
    if (typeof cb === 'function') {
      cb();
    }
  }, 75);
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
  resetVisualTints();
  el.style.transition = 'none';
  el.style.transform = 'translate3d(0, 0, 0) scale(1)';
  el.style.opacity = '1';
  const backdrop = getBackdrop();
  if (backdrop) {
    backdrop.style.transition = 'none';
    backdrop.style.transform = 'translate3d(0, 8px, 0) scale(0.94)';
    backdrop.style.opacity = '0.70';
  }
}

export function resetCardPosition(cardEl) {
  const el = cardEl || document.getElementById('ankiCardContainer');
  if (!el) return;
  el.style.transition =
    'transform 0.22s cubic-bezier(0.175, 0.885, 0.32, 1.275), opacity 0.18s ease-out';
  el.style.transform = 'translate3d(0, 0, 0) scale(1) rotate(0deg)';
  el.style.opacity = '1';
  resetBackdropPosition();
  resetVisualTints();
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
