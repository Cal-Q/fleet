// static/js/modules/drag_scroll.js — Mobile-Style Cursor Drag-To-Scroll
// Strictly <= 200 lines invariant.

let activeEl = null;
let isDown = false;
let isDragging = false;
let startX = 0;
let startY = 0;
let startScrollTop = 0;
let startScrollLeft = 0;
let lastY = 0;
let lastTime = 0;
let velocityY = 0;
let momentumFrame = null;

function findScrollable(el) {
  while (el && el !== document.body && el !== document.documentElement) {
    if (el.classList && (el.classList.contains('overflow-y-auto') || el.classList.contains('overflow-x-auto') || el.hasAttribute('data-drag-scroll'))) {
      return el;
    }
    el = el.parentElement;
  }
  return null;
}

export function initDragScroll() {
  document.addEventListener('mousedown', (e) => {
    if (e.button !== 0) return; // Primary click only
    const targetTag = e.target.tagName.toLowerCase();
    if (['input', 'textarea', 'select', 'option'].includes(targetTag)) return;

    const scrollable = findScrollable(e.target);
    if (!scrollable) return;

    if (momentumFrame) {
      cancelAnimationFrame(momentumFrame);
      momentumFrame = null;
    }

    activeEl = scrollable;
    isDown = true;
    isDragging = false;
    startX = e.clientX;
    startY = e.clientY;
    lastY = e.clientY;
    lastTime = performance.now();
    startScrollTop = scrollable.scrollTop;
    startScrollLeft = scrollable.scrollLeft;
    velocityY = 0;
  }, { passive: true });

  document.addEventListener('mousemove', (e) => {
    if (!isDown || !activeEl) return;

    const dy = e.clientY - startY;
    const dx = e.clientX - startX;

    if (!isDragging && (Math.abs(dy) > 4 || Math.abs(dx) > 4)) {
      isDragging = true;
      document.body.classList.add('is-dragging-active');
    }

    if (isDragging) {
      activeEl.scrollTop = startScrollTop - dy;
      activeEl.scrollLeft = startScrollLeft - dx;

      const now = performance.now();
      const dt = now - lastTime;
      if (dt > 0) {
        velocityY = (e.clientY - lastY) / dt;
        lastTime = now;
        lastY = e.clientY;
      }
    }
  }, { passive: true });

  const endDrag = () => {
    if (!isDown) return;
    isDown = false;

    if (isDragging) {
      document.body.classList.remove('is-dragging-active');

      // Prevent accidental click on links/buttons after drag
      const captureClick = (ev) => {
        ev.stopPropagation();
        ev.preventDefault();
        window.removeEventListener('click', captureClick, true);
      };
      window.addEventListener('click', captureClick, true);
      setTimeout(() => window.removeEventListener('click', captureClick, true), 80);

      // Inertia Momentum Coasting
      if (activeEl && Math.abs(velocityY) > 0.15) {
        const momentumEl = activeEl;
        let vel = velocityY * 16;
        const coast = () => {
          if (Math.abs(vel) < 0.5) return;
          momentumEl.scrollTop -= vel;
          vel *= 0.92;
          momentumFrame = requestAnimationFrame(coast);
        };
        momentumFrame = requestAnimationFrame(coast);
      }
    }

    activeEl = null;
    isDragging = false;
  };

  document.addEventListener('mouseup', endDrag, { passive: true });
  document.addEventListener('mouseleave', endDrag, { passive: true });
}
