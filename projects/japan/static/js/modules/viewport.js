// static/js/modules/viewport.js — GPU Accelerated Stage Viewport with 60fps Gestures
// Based on Sinoira Gang (pokemon.calq.it) StageViewport architecture.
// Strictly <= 200 lines invariant.

import { STAGE_CONFIG, updateDockProgress, setActiveStage, setDockTransition } from './dock.js';

let containerEl = null;
let trackEl = null;
let currentIndex = 0;
let isDragging = false;
let isHorizontalGesture = null;
let startX = 0;
let startY = 0;
let currentPx = 0;
let lastX = 0;
let lastTime = 0;
let velocity = 0;
let animTimer = null;

function setTrackTransition(durationMs, easing = 'cubic-bezier(0.25, 1, 0.5, 1)') {
  if (!trackEl) return;
  trackEl.style.transition = durationMs > 0 ? `transform ${durationMs}ms ${easing}` : 'none';
}

export function snapToStageIndex(index, animate = true) {
  if (!containerEl || !trackEl) return;
  const count = STAGE_CONFIG.length;
  const target = Math.max(0, Math.min(count - 1, index));
  currentIndex = target;
  currentPx = -target * containerEl.clientWidth;

  if (animTimer) {
    clearTimeout(animTimer);
    animTimer = null;
  }

  setDockTransition(animate);
  setTrackTransition(animate ? 320 : 0);

  trackEl.style.transform = `translate3d(${-target * 100}%, 0, 0)`;
  updateDockProgress(target);

  const notify = () => {
    const k = STAGE_CONFIG[target]?.key;
    if (k && typeof window.onStageActivated === 'function') window.onStageActivated(k);
  };
  if (animate) {
    animTimer = setTimeout(() => {
      setTrackTransition(0);
      setDockTransition(false);
      notify();
    }, 320);
  } else {
    notify();
  }
}

function onDragStart(clientX, clientY) {
  if (!containerEl || !trackEl) return;
  if (animTimer) {
    clearTimeout(animTimer);
    animTimer = null;
  }

  startX = clientX;
  startY = clientY;
  lastX = clientX;
  lastTime = performance.now();
  velocity = 0;
  isDragging = true;
  isHorizontalGesture = null;

  currentPx = -currentIndex * containerEl.clientWidth;
  setTrackTransition(0);
  setDockTransition(false);
}

function onDragMove(clientX, clientY, e) {
  if (!isDragging || !containerEl || !trackEl) return;
  const dx = clientX - startX;
  const dy = clientY - startY;

  if (isHorizontalGesture === null) {
    if (Math.abs(dx) > 7 || Math.abs(dy) > 7) {
      isHorizontalGesture = Math.abs(dx) >= Math.abs(dy);
      if (!isHorizontalGesture) {
        isDragging = false;
        return;
      }
    } else {
      return;
    }
  }

  if (!isHorizontalGesture) return;
  if (e && e.cancelable) e.preventDefault();

  const now = performance.now();
  const dt = now - lastTime;
  if (dt > 8) {
    velocity = (clientX - lastX) / dt;
    lastX = clientX;
    lastTime = now;
  }

  const w = containerEl.clientWidth;
  const minPx = -(STAGE_CONFIG.length - 1) * w;
  let nextPx = (-currentIndex * w) + dx;

  // Elastic rubber-band resistance at boundaries (Sinoira Gang dragElastic: 0.15)
  if (nextPx > 0) {
    nextPx = nextPx * 0.18;
  } else if (nextPx < minPx) {
    nextPx = minPx + (nextPx - minPx) * 0.18;
  }

  currentPx = nextPx;
  trackEl.style.transform = `translate3d(${nextPx}px, 0, 0)`;

  const rawProgress = -nextPx / w;
  updateDockProgress(rawProgress);
}

function onDragEnd() {
  if (!isDragging || !containerEl) return;
  isDragging = false;
  if (!isHorizontalGesture) return;

  const w = containerEl.clientWidth;
  const currentProgress = -currentPx / w;
  let target = Math.round(currentProgress);

  // Velocity fling detection (> 0.25 px/ms)
  if (velocity < -0.25) {
    target = Math.ceil(currentProgress);
  } else if (velocity > 0.25) {
    target = Math.floor(currentProgress);
  }

  target = Math.max(0, Math.min(STAGE_CONFIG.length - 1, target));
  snapToStageIndex(target, true);

  const stageKey = STAGE_CONFIG[target]?.key;
  if (stageKey) {
    setActiveStage(stageKey, false);
  }
}

export function initViewport() {
  containerEl = document.getElementById('stageViewportContainer');
  trackEl = document.getElementById('stageViewportTrack');
  if (!containerEl || !trackEl) return;

  let lastTouchTs = 0;
  containerEl.addEventListener('touchstart', (e) => {
    lastTouchTs = performance.now();
    if (e.touches.length === 1) onDragStart(e.touches[0].clientX, e.touches[0].clientY);
  }, { passive: true });

  containerEl.addEventListener('touchmove', (e) => {
    lastTouchTs = performance.now();
    if (e.touches.length === 1) onDragMove(e.touches[0].clientX, e.touches[0].clientY, e);
  }, { passive: false });

  containerEl.addEventListener('touchend', onDragEnd, { passive: true });
  containerEl.addEventListener('touchcancel', onDragEnd, { passive: true });

  let isMouseDown = false;
  containerEl.addEventListener('mousedown', (e) => {
    if (e.button !== 0 || performance.now() - lastTouchTs < 600) return;
    isMouseDown = true;
    onDragStart(e.clientX, e.clientY);
  });
  window.addEventListener('mousemove', (e) => { if (isMouseDown) onDragMove(e.clientX, e.clientY, e); });
  window.addEventListener('mouseup', () => { if (isMouseDown) { isMouseDown = false; onDragEnd(); } });

  window.snapToStageIndex = snapToStageIndex;
  window.scrollToStageIndex = snapToStageIndex;
  window.addEventListener('resize', () => { if (containerEl) snapToStageIndex(currentIndex, false); }, { passive: true });
}

