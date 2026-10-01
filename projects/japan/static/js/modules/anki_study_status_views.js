// static/js/modules/anki_study_status_views.js — Session Completion & Cooldown Screens
// Strictly <= 200 lines, <= 100 cols invariant.

const get = (id) => document.getElementById(id);

export function renderLearningCooldownWaiting(remainingSec, onLearnAhead, onExit) {
  const frontEl = get('ankiCardFront');
  const backEl = get('ankiCardBack');
  const promptEl = get('ankiFlipPrompt');
  const btnShow = get('ankiBtnShowAnswer');
  const btnGroup = get('ankiAnswerButtonGroup');
  const swipeHints = get('ankiSwipeHintsBar');

  const cardCont = get('ankiCardContainer');
  if (cardCont) {
    cardCont.style.transition = 'none';
    cardCont.style.transform = 'translate3d(0, 0, 0) scale(1) rotate(0deg)';
    cardCont.style.opacity = '1';
  }
  const backdrop = get('ankiCardBackdrop');
  if (backdrop) {
    backdrop.style.transition = 'none';
    backdrop.style.transform = 'translate3d(0, 8px, 0) scale(0.94)';
    backdrop.style.opacity = '0.80';
  }

  if (backEl) backEl.classList.add('hidden');
  if (promptEl) promptEl.classList.add('hidden');
  if (btnGroup) btnGroup.classList.add('hidden');
  if (swipeHints) swipeHints.classList.add('hidden');

  const min = Math.floor(Math.max(0, remainingSec) / 60);
  const sec = Math.max(0, remainingSec) % 60;
  const timeStr = `${min}:${sec.toString().padStart(2, '0')}`;

  if (frontEl) {
    frontEl.style.fontSize = '';
    frontEl.innerHTML = `
      <div class="space-y-4 py-3 animate-info-fade select-none">
        <div class="text-4xl animate-pulse">⏳</div>
        <div class="text-base sm:text-lg font-bold text-white tracking-wide">
          In attesa del Cooldown
        </div>
        <div class="text-xs text-neutral-400 font-mono max-w-xs mx-auto leading-relaxed">
          Prossima carta rossa in apprendimento tra:
        </div>
        <div id="ankiCooldownDisplay"
          class="text-3xl font-mono font-bold text-[#EF5350] tracking-wider py-1">
          ${timeStr}
        </div>
        <div class="flex flex-col gap-2 max-w-xs mx-auto pt-2 pointer-events-auto">
          <button id="btnLearnAhead"
            class="w-full py-2.5 bg-[#EF5350]/20 hover:bg-[#EF5350]/30 active:scale-95
            text-[#EF5350] border border-[#EF5350]/40 font-bold text-xs uppercase
            tracking-wider rounded-xl transition tap-press flex items-center justify-center
            gap-1.5 shadow-sm">
            <span>⚡ Ripassa Subito (Learn Ahead)</span>
          </button>
          <button id="btnCooldownExit"
            class="w-full py-2 bg-white/5 hover:bg-white/10 active:scale-95 text-neutral-400
            font-mono text-xs rounded-xl transition tap-press">
            <span>Torna ai Mazzi ➔</span>
          </button>
        </div>
      </div>
    `;
    const btnAhead = get('btnLearnAhead');
    if (btnAhead && onLearnAhead) btnAhead.onclick = onLearnAhead;
    const btnExit = get('btnCooldownExit');
    if (btnExit && onExit) btnExit.onclick = onExit;
  }
  if (btnShow) btnShow.classList.add('hidden');
}

export function renderSessionFinished() {
  const frontEl = get('ankiCardFront');
  const backEl = get('ankiCardBack');
  const promptEl = get('ankiFlipPrompt');
  const btnShow = get('ankiBtnShowAnswer');
  const btnGroup = get('ankiAnswerButtonGroup');
  const swipeHints = get('ankiSwipeHintsBar');
  const swipeZone = get('ankiCardSwipeZone');
  const timerCont = get('ankiTimerContainer');
  const cardCont = get('ankiCardContainer');
  const topZone = get('ankiCardTopZone');

  if (cardCont) {
    cardCont.style.transition = 'none';
    cardCont.style.transform = 'translate3d(0, 0, 0) scale(1) rotate(0deg)';
    cardCont.style.opacity = '1';
  }
  const backdrop = get('ankiCardBackdrop');
  if (backdrop) {
    backdrop.style.transition = 'none';
    backdrop.style.transform = 'translate3d(0, 8px, 0) scale(0.94)';
    backdrop.style.opacity = '0.80';
  }
  if (swipeZone) swipeZone.classList.add('hidden');
  if (timerCont) timerCont.classList.add('hidden');
  if (topZone) {
    topZone.classList.add('my-auto');
    topZone.classList.remove('pt-2');
  }
  if (backEl) backEl.classList.add('hidden');
  if (promptEl) promptEl.classList.add('hidden');
  if (btnGroup) btnGroup.classList.add('hidden');
  if (swipeHints) swipeHints.classList.add('hidden');

  if (frontEl) {
    frontEl.style.fontSize = '';
    frontEl.innerHTML = `
      <div class="space-y-4 py-4 animate-info-fade">
        <div class="text-5xl">🎉</div>
        <div class="text-xl sm:text-2xl font-bold text-white tracking-wide">
          Mazzo Completato!
        </div>
        <div class="text-xs sm:text-sm text-neutral-400 font-mono max-w-xs mx-auto leading-relaxed">
          Tutti i ripassi e le nuove carte per questo mazzo sono terminati per oggi.
        </div>
        <div class="pt-3">
          <button onclick="window.ankiShowDeckList()"
            class="px-8 py-3 bg-[#2196F3] hover:bg-[#1E88E5] text-white font-bold text-xs
            uppercase tracking-wider rounded-xl shadow-lg transition tap-press active:scale-95
            flex items-center justify-center gap-2 mx-auto">
            <span>Torna ai Mazzi</span><span class="text-xs opacity-70">➔</span>
          </button>
        </div>
      </div>
    `;
  }
  if (btnShow) {
    btnShow.classList.remove('hidden');
    btnShow.innerHTML = '<span>Torna ai Mazzi ➔</span>';
    btnShow.onclick = () => window.ankiShowDeckList();
  }
}
