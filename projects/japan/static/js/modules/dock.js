// static/js/modules/dock.js — Tactile Bottom Dock Navigation with Real-Time Sliding Pill
// Based on Sinoira Gang (pokemon.calq.it) StageDockNav architecture.
// Strictly <= 200 lines invariant.

export const STAGE_CONFIG = [
  { key: 'routine', label: 'Routine', kanji: '日課', hotkey: '1', color: '#181A1B' },
  { key: 'study', label: 'Studio', kanji: '学習', hotkey: '2', color: '#264332' },
  { key: 'bunki', label: 'Bunki', kanji: '復習', hotkey: '3', color: '#1E2C3A' },
  { key: 'exams', label: 'Prove', kanji: '試練', hotkey: '4', color: '#C23B22' },
  { key: 'dossier', label: 'Dossier', kanji: '計画', hotkey: '5', color: '#8B5A2B' }
];

let activeStageKey = 'routine';
let cachedPill = null;
let cachedAccentBar = null;
let cachedTopPill = null;
let cachedTopStageLabel = null;
let cachedButtons = [];
let lastCoveredIdx = -1;

export function getActiveStage() {
  return activeStageKey;
}

export function setDockTransition(enabled) {
  const t = enabled ? 'transform 320ms cubic-bezier(0.25, 1, 0.5, 1)' : 'none';
  if (cachedPill) cachedPill.style.transition = t;
  if (cachedTopPill) cachedTopPill.style.transition = t;
}

export function updateDockProgress(progress) {
  const count = STAGE_CONFIG.length;
  const clamped = Math.max(0, Math.min(count - 1, progress));
  const roundedIdx = Math.round(clamped);
  const currentItem = STAGE_CONFIG[roundedIdx] || STAGE_CONFIG[0];

  if (cachedPill) {
    cachedPill.style.transform = `translate3d(${clamped * 100}%, 0, 0)`;
  }
  if (cachedTopPill) {
    cachedTopPill.style.transform = `translate3d(${clamped * 100}%, 0, 0)`;
  }
  if (cachedAccentBar && currentItem) {
    cachedAccentBar.style.backgroundColor = currentItem.color;
  }

  // Update button active typography only when active index shifts
  if (roundedIdx !== lastCoveredIdx) {
    lastCoveredIdx = roundedIdx;
    cachedButtons.forEach((entry, idx) => {
      const isCovered = (idx === roundedIdx);
      if (entry.btn) {
        entry.btn.classList.toggle('text-white', isCovered);
        entry.btn.classList.toggle('font-bold', isCovered);
        entry.btn.classList.toggle('text-neutral-500', !isCovered);
        if (entry.icon) {
          entry.icon.style.color = isCovered ? entry.it.color : '';
        }
      }
    });

    if (cachedTopStageLabel && currentItem) {
      cachedTopStageLabel.innerText = `${currentItem.kanji} ${currentItem.label.toUpperCase()}`;
      cachedTopStageLabel.style.color = currentItem.color;
    }
  }
}

export function setActiveStage(key, triggerTrack = true) {
  const targetIdx = STAGE_CONFIG.findIndex(s => s.key === key);
  if (targetIdx === -1) return;
  activeStageKey = key;

  setDockTransition(true);
  updateDockProgress(targetIdx);

  if (triggerTrack && typeof window.snapToStageIndex === 'function') {
    window.snapToStageIndex(targetIdx, true);
  }

  if (typeof window.onStageActivated === 'function') {
    window.onStageActivated(key);
  }
}

export function initDock() {
  cachedPill = document.getElementById('dockSlidingPill');
  cachedAccentBar = document.getElementById('dockAccentBar');
  cachedTopPill = document.getElementById('topTrackPill');
  cachedTopStageLabel = document.getElementById('topStageLabel');

  cachedButtons = STAGE_CONFIG.map(it => ({
    it,
    btn: document.getElementById(`dockBtn_${it.key}`),
    icon: document.querySelector(`#dockBtn_${it.key} .dock-kanji`)
  }));

  STAGE_CONFIG.forEach((it) => {
    const btn = document.getElementById(`dockBtn_${it.key}`);
    if (btn) {
      btn.onclick = () => setActiveStage(it.key, true);
    }
    const topDot = document.getElementById(`topDot_${it.key}`);
    if (topDot) {
      topDot.onclick = () => setActiveStage(it.key, true);
    }
  });

  // Keyboard numbers 1-5 direct navigation
  window.addEventListener('keydown', (e) => {
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) return;
    const num = parseInt(e.key, 10);
    if (num >= 1 && num <= STAGE_CONFIG.length) {
      e.preventDefault();
      setActiveStage(STAGE_CONFIG[num - 1].key, true);
    }
  });

  setDockTransition(false);
  updateDockProgress(0);
}

