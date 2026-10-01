// static/js/modules/anki_web_session_timer_ui.js — UI & Modal Renderer for Timer Hub
// Strictly <= 200 lines invariant.

const get = id => document.getElementById(id);
let _activeTimerTab = 'session';

export function formatMinSec(totalSec) {
  const m = Math.floor(totalSec / 60), s = totalSec % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

export function openSessionTimerModal(sessionState, cardState, initialTab = 'session') {
  const modal = get('ankiSessionTimerModal');
  if (!modal) return;
  modal.classList.remove('hidden');
  switchTimerTab(initialTab);
  updateModalTimerUI(sessionState, cardState);
}

export function closeSessionTimerModal() {
  const modal = get('ankiSessionTimerModal');
  if (modal) modal.classList.add('hidden');
}

export function switchTimerTab(tab) {
  _activeTimerTab = tab === 'card' ? 'card' : 'session';
  const btnSess = get('btnTimerTabSession'), btnCard = get('btnTimerTabCard');
  const cntSess = get('ankiTimerTabSessionContent'), cntCard = get('ankiTimerTabCardContent');

  if (_activeTimerTab === 'session') {
    if (btnSess) btnSess.className = 'px-2.5 py-1 rounded-md text-[11px] font-bold transition tap-press bg-[#2196F3] text-white shadow-sm';
    if (btnCard) btnCard.className = 'px-2.5 py-1 rounded-md text-[11px] font-bold transition tap-press text-neutral-400 hover:text-white';
    if (cntSess) cntSess.classList.remove('hidden');
    if (cntCard) cntCard.classList.add('hidden');
  } else {
    if (btnSess) btnSess.className = 'px-2.5 py-1 rounded-md text-[11px] font-bold transition tap-press text-neutral-400 hover:text-white';
    if (btnCard) btnCard.className = 'px-2.5 py-1 rounded-md text-[11px] font-bold transition tap-press bg-[#FFA726] text-black shadow-sm';
    if (cntSess) cntSess.classList.add('hidden');
    if (cntCard) cntCard.classList.remove('hidden');
  }
}

export function updateSessionTimerUI(_state) {}

export function updateModalTimerUI(sessionState, cardState) {
  const modal = get('ankiSessionTimerModal');
  if (!modal || modal.classList.contains('hidden')) return;

  renderSessionTabUI(sessionState);
  if (cardState) renderCardTabUI(cardState);
}

function renderSessionTabUI(state) {
  const statusEl = get('ankiModalTimerStatus'), displayEl = get('ankiModalTimerDisplay');
  const subtextEl = get('ankiModalTimerSubtext'), durLabel = get('ankiModalSelectedDuration');
  const pauseBtnIcon = get('ankiModalPauseResumeIcon'), pauseBtnText = get('ankiModalPauseResumeText');
  const customInput = get('ankiModalCustomMinInput');

  if (durLabel) durLabel.innerText = state.targetMin > 0 ? `${state.targetMin} min` : 'Libero (Cronometro)';
  if (customInput && document.activeElement !== customInput) customInput.value = state.targetMin > 0 ? state.targetMin : 25;

  if (pauseBtnIcon && pauseBtnText) {
    if (state.isRunning) { pauseBtnIcon.innerText = '⏸'; pauseBtnText.innerText = 'Pausa'; }
    else { pauseBtnIcon.innerText = '▶'; pauseBtnText.innerText = state.isCompleted ? 'Riavvia' : 'Riprendi'; }
  }

  if (state.isCompleted) {
    if (statusEl) { statusEl.innerText = '🎉 Target Raggiunto!'; statusEl.className = 'text-[11px] text-[#66BB6A] font-bold uppercase tracking-wider animate-bounce'; }
    if (displayEl) { displayEl.innerText = '00:00'; displayEl.className = 'text-4xl font-mono font-bold text-[#66BB6A] tracking-wider'; }
    if (subtextEl) subtextEl.innerText = `Sessione di ${state.targetMin} min completata!`;
  } else if (state.targetMin <= 0) {
    if (statusEl) { statusEl.innerText = state.isRunning ? '⏱️ Cronometro in Corso' : '⏸ In Pausa'; statusEl.className = 'text-[10px] text-[#42A5F5] font-bold uppercase tracking-wider'; }
    if (displayEl) { displayEl.innerText = formatMinSec(state.elapsedSec); displayEl.className = 'text-4xl font-mono font-bold text-[#42A5F5] tracking-wider'; }
    if (subtextEl) subtextEl.innerText = 'Modalità conteggio libero senza scadenza';
  } else {
    const remain = Math.max(0, state.targetMin * 60 - state.elapsedSec);
    if (statusEl) { statusEl.innerText = state.isRunning ? '🎯 Sessione in Corso' : '⏸ In Pausa'; statusEl.className = 'text-[10px] text-neutral-400 font-bold uppercase tracking-wider'; }
    if (displayEl) {
      displayEl.innerText = formatMinSec(remain);
      displayEl.className = remain > 300 ? 'text-4xl font-mono font-bold text-[#66BB6A] tracking-wider' : 'text-4xl font-mono font-bold text-[#FFA726] tracking-wider animate-pulse';
    }
    if (subtextEl) subtextEl.innerText = `Target: ${state.targetMin} min (trascorsi ${formatMinSec(state.elapsedSec)})`;
  }

  document.querySelectorAll('.anki-timer-preset-btn').forEach(btn => {
    const val = parseInt(btn.dataset.modalMin, 10) || 0;
    btn.className = (val === state.targetMin)
      ? 'anki-timer-preset-btn py-1.5 rounded-lg border border-[#66BB6A] bg-[#66BB6A]/20 text-white font-semibold text-center transition tap-press shadow-sm'
      : 'anki-timer-preset-btn py-1.5 rounded-lg border border-[#2C2C2C] bg-[#2A2A2A] text-neutral-300 font-semibold text-center transition tap-press hover:border-neutral-500';
  });
}

function renderCardTabUI(cardState) {
  const deckLabel = get('ankiCardTimerDeckLabel');
  const durDisplay = get('ankiModalCardTimerDisplay');
  const slider = get('sliderModalCardTimer');
  const sliderLabel = get('labelModalCardTimerSlider');

  const dur = cardState.duration || 0;
  if (deckLabel) {
    const dName = cardState.name || 'Tutti i Mazzi';
    deckLabel.innerText = `Mazzo: ${dName}`;
  }
  if (durDisplay) {
    durDisplay.innerText = dur > 0 ? `${dur}s` : 'Off (Libero)';
    durDisplay.className = dur > 0 ? 'text-[#FFA726] font-bold' : 'text-[#42A5F5] font-bold';
  }
  if (slider) slider.value = dur;
  if (sliderLabel) sliderLabel.innerText = dur > 0 ? `${dur}s` : 'Off';

  document.querySelectorAll('.anki-card-timer-preset-btn').forEach(btn => {
    const val = parseInt(btn.dataset.cardSec, 10) || 0;
    btn.className = (val === dur)
      ? 'anki-card-timer-preset-btn py-1.5 rounded-lg border border-[#FFA726] bg-[#FFA726]/20 text-white font-semibold text-center transition tap-press shadow-sm'
      : 'anki-card-timer-preset-btn py-1.5 rounded-lg border border-[#2C2C2C] bg-[#2A2A2A] text-neutral-300 font-semibold text-center transition tap-press hover:border-neutral-500';
  });
}
