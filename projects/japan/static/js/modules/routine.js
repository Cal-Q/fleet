// static/js/modules/routine.js — Automated Daily Study Routine Dispatch & Tracking
// Strictly <= 200 lines invariant.

const ROUTINE_CONFIG = {
  1: {
    key: 'slot1',
    seal: '壱',
    color: '#181A1B',
    stage: 'bunki',
    action: () => { if (typeof window.loadBunkiProfile === 'function') window.loadBunkiProfile(); },
    guide: 'Fase 1 • Slot 1: Ripasso SRS (1h) — Mantieni le 5.052 mature Anki a zero arretrati. Convalida automatica.'
  },
  2: {
    key: 'slot2',
    seal: '弐',
    color: '#264332',
    stage: 'study',
    action: () => { if (typeof window.switchStudyBranch === 'function') window.switchStudyBranch('grammar'); },
    guide: 'Fase 1 • Slot 2: Sprint N4 (1h15m) — Completa 3.1 lezioni Bunpro/die per chiudere N4 al 100% entro il 28/09.'
  },
  3: {
    key: 'slot3',
    seal: '参',
    color: '#1E2C3A',
    stage: 'exams',
    action: () => { if (typeof window.switchExamBranch === 'function') window.switchExamBranch('interview'); },
    guide: 'Fase 1 • Slot 3: Keigo & Verbi (45m) — Pratica le 12 forme irregolari (Sonkeigo/Kenjōgo) e coppie transitivo/intransitivo.'
  },
  4: {
    key: 'slot4',
    seal: '肆',
    color: '#C23B22',
    stage: 'exams',
    action: () => { if (typeof window.loadExam === 'function') window.loadExam('A'); },
    guide: 'Fase 1 • Slot 4: Drill Part A (1h) — Esercitati solo sui quesiti di Part A (target 95% = 33/35 pt).'
  }
};

export function initDailyRoutine() {
  const todayStr = new Date().toISOString().split('T')[0];
  const storageKey = 'mext_routine_' + todayStr;
  const state = JSON.parse(localStorage.getItem(storageKey) || '{}');

  // Auto-clean false slot2 completion if not explicitly confirmed
  if (state.slot2 && !state.slot2_manually_confirmed) {
    delete state.slot2;
    localStorage.setItem(storageKey, JSON.stringify(state));
  }

  updateRoutineProgress(state);
}

export function toggleRoutineSlot(slotKey) {
  const todayStr = new Date().toISOString().split('T')[0];
  const storageKey = 'mext_routine_' + todayStr;
  const state = JSON.parse(localStorage.getItem(storageKey) || '{}');

  if (state[slotKey]) {
    delete state[slotKey];
    delete state[slotKey + '_manually_confirmed'];
  } else {
    state[slotKey] = true;
    state[slotKey + '_manually_confirmed'] = true;
  }
  localStorage.setItem(storageKey, JSON.stringify(state));
  updateRoutineProgress(state);
}

export function launchRoutineSlot(slotNum) {
  const conf = ROUTINE_CONFIG[slotNum];
  if (!conf) return;

  if (typeof window.setActiveStage === 'function') {
    window.setActiveStage(conf.stage, true);
  }
  if (typeof conf.action === 'function') {
    conf.action();
  }

  showGuidanceBanner(conf.seal, conf.color, conf.guide);
}

export function markRoutineSlotDone(slotKey) {
  const todayStr = new Date().toISOString().split('T')[0];
  const storageKey = 'mext_routine_' + todayStr;
  const state = JSON.parse(localStorage.getItem(storageKey) || '{}');
  
  if (!state[slotKey]) {
    state[slotKey] = true;
    localStorage.setItem(storageKey, JSON.stringify(state));
    updateRoutineProgress(state);
    if (typeof window.syncSlot1UI === 'function') window.syncSlot1UI();
    
    // Notify automated completion with next step prompt
    const nextMap = { slot1: 2, slot2: 3, slot3: 4 };
    const nextNum = nextMap[slotKey];
    if (nextNum) {
      showGuidanceBanner('✓', '#264332', `Completamento registrato per ${slotKey.toUpperCase()}! Clicca qui per procedere allo Slot ${nextNum} →`, nextNum);
    } else {
      showGuidanceBanner('🎉', '#264332', 'Tutti i 4 Slot della Routine Giornaliera sono stati completati!');
    }
  }
}

export function unmarkRoutineSlot(slotKey) {
  const todayStr = new Date().toISOString().split('T')[0];
  const storageKey = 'mext_routine_' + todayStr;
  const state = JSON.parse(localStorage.getItem(storageKey) || '{}');
  
  if (state[slotKey]) {
    delete state[slotKey];
    localStorage.setItem(storageKey, JSON.stringify(state));
    updateRoutineProgress(state);
    if (typeof window.syncSlot1UI === 'function') window.syncSlot1UI();
  }
}

function showGuidanceBanner(seal, color, message, nextSlotNum = null) {
  const banner = document.getElementById('routineGuidanceBanner');
  const sealEl = document.getElementById('guidanceSlotSeal');
  const textEl = document.getElementById('guidanceSlotText');

  if (!banner || !sealEl || !textEl) return;

  sealEl.innerText = seal;
  sealEl.style.backgroundColor = color;
  banner.style.borderLeftColor = color;
  textEl.innerText = message;
  
  if (nextSlotNum) {
    banner.style.cursor = 'pointer';
    banner.onclick = () => launchRoutineSlot(nextSlotNum);
  } else {
    banner.style.cursor = 'default';
    banner.onclick = null;
  }
  
  banner.classList.remove('hidden');

  if (window._guidanceTimer) clearTimeout(window._guidanceTimer);
  window._guidanceTimer = setTimeout(() => {
    banner.classList.add('hidden');
  }, 10000);
}

export function updateRoutineProgress(state) {
  const slots = ['slot1', 'slot2', 'slot3', 'slot4'];
  const completedCount = slots.filter(s => state[s]).length;
  const pct = Math.round((completedCount / slots.length) * 100);

  slots.forEach((slot, idx) => {
    const card = document.getElementById(`slotCard${idx + 1}`);
    const pill = document.getElementById(`slot${idx + 1}StatusPill`);
    const isDone = !!state[slot];

    if (card) {
      card.classList.toggle('bg-[#EEF7F1]', isDone);
      card.classList.toggle('border-[#264332]/40', isDone);
      card.classList.toggle('bg-[#FAF8F5]', !isDone);
    }
    if (pill) {
      if (isDone) {
        pill.className = 'text-[10px] font-mono font-bold px-1.5 py-0.5 border border-[#264332]/30 bg-[#EEF7F1] text-[#264332] flex items-center gap-1';
        pill.innerHTML = '<span>✓ FATTO</span>';
      } else {
        pill.className = 'text-[10px] font-mono font-bold px-1.5 py-0.5 border border-black/20 bg-white text-neutral-600 flex items-center gap-1';
        pill.innerHTML = '<span>→ VAI</span>';
      }
    }
  });

  const bar = document.getElementById('routineProgressBar');
  const text = document.getElementById('routineProgressText');

  if (bar) bar.style.width = pct + '%';
  if (text) {
    text.innerText = `${completedCount}/4h Completate (${completedCount}/4 Slot • ${pct}%)`;
    text.className = completedCount === 4 ? 'text-[#264332] font-bold' : 'text-[#181A1B] font-bold';
  }
}

