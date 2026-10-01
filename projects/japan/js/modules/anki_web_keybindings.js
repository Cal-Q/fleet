// static/js/modules/anki_web_keybindings.js
// Physical Keyboard Shortcuts & Action Routing (<= 200 lines, <= 100 cols)

export function initCardKeybindings(
  isFlippedFn,
  onSwipeFn,
  onFlipFn,
  onUndoFn,
  onResetTimerFn = null,
  onAltRuleFn = null,
  getRemainingRatioFn = null
) {
  window.addEventListener('keydown', (e) => {
    const activeEl = document.activeElement;
    if (activeEl && (
      ['INPUT', 'TEXTAREA', 'SELECT'].includes(activeEl.tagName) ||
      activeEl.isContentEditable
    )) {
      return;
    }
    const sView = document.getElementById('ankiStudyView');
    if (!sView || sView.classList.contains('hidden')) return;

    const flipped = typeof isFlippedFn === 'function' ? isFlippedFn() : false;

    if (e.key === 'z' || (e.key === 'z' && (e.ctrlKey || e.metaKey))) {
      e.preventDefault();
      if (typeof onUndoFn === 'function') onUndoFn();
      return;
    }

    if ((e.key === 'r' || e.key === 'R') && typeof onResetTimerFn === 'function') {
      e.preventDefault();
      onResetTimerFn();
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (flipped) {
        if (typeof onUndoFn === 'function') onUndoFn();
        return;
      }
      const rem = typeof getRemainingRatioFn === 'function'
        ? getRemainingRatioFn()
        : 1.0;
      if (rem < 0.5 && typeof onResetTimerFn === 'function') {
        onResetTimerFn();
      } else if (typeof onUndoFn === 'function') {
        onUndoFn();
      }
      return;
    }

    if (e.key === 'ArrowUp' && typeof onAltRuleFn === 'function') {
      e.preventDefault();
      onAltRuleFn();
      return;
    }

    if (e.code === 'Space' || e.key === 'Enter') {
      e.preventDefault();
      if (!flipped) {
        if (typeof onFlipFn === 'function') onFlipFn();
      } else {
        if (typeof onSwipeFn === 'function') onSwipeFn(3);
      }
      return;
    }

    if (flipped) {
      if (e.key === '1' || e.key === 'ArrowLeft') {
        e.preventDefault();
        if (typeof onSwipeFn === 'function') onSwipeFn(1);
      } else if (e.key === '2' || e.key === 'ArrowRight') {
        e.preventDefault();
        if (typeof onSwipeFn === 'function') onSwipeFn(3);
      }
    }
  });
}
