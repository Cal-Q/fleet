import { triggerProgrammaticSwipe } from './anki_web_gestures.js';
export { triggerProgrammaticSwipe };
// static/js/modules/anki_web_study.js — AnkiDroid Study Card Renderer (WRONG vs CORRECT)
// Strictly <= 200 lines invariant.
import { applyFontSizes, getFuriganaMode } from './anki_web_settings.js';
import { renderReadingsAndMeanings } from './anki_web_meanings.js';

let _activeCard = null;
let _isFlipped = false;
let _currentDeck = null;

export function setCurrentDeck(id, name) {
  if (id === null) {
    _currentDeck = null;
  } else {
    _currentDeck = { id: Number(id), name: name, display_name: name };
  }
}

export function getSelectedDeck() {
  return _currentDeck;
}

export function getActiveCard() {
  return _activeCard;
}

export function renderStudyHeader(counts, currentNum, total) {
  const cNew = document.getElementById('ankiCountNew');
  const cLrn = document.getElementById('ankiCountLrn');
  const cRev = document.getElementById('ankiCountRev');
  if (cNew) cNew.innerText = counts.new;
  if (cLrn) cLrn.innerText = counts.learning;
  if (cRev) cRev.innerText = counts.review;
}

export function getFrontContent(card) {
  if (!card) return '';
  const mode = getFuriganaMode();
  if (mode === 'always') {
    return card.ruby_all || card.front;
  } else if (mode === 'unstudied') {
    return card.ruby_unstudied || card.front;
  }
  return card.front;
}

export function updateCardElements(card, isFlipped) {
  if (!card) return;
  _activeCard = card;
  _isFlipped = isFlipped;

  const frontEl = document.getElementById('ankiCardFront');
  const backEl = document.getElementById('ankiCardBack'), promptEl = document.getElementById('ankiFlipPrompt');
  const readingEl = document.getElementById('ankiCardReading'), meaningEl = document.getElementById('ankiCardMeaning');
  const notesEl = document.getElementById('ankiCardNotes'), scrollEl = document.getElementById('ankiCardMeaningScroll');
  const btnShow = document.getElementById('ankiBtnShowAnswer'), btnGroup = document.getElementById('ankiAnswerButtonGroup');
  const swipeHints = document.getElementById('ankiSwipeHintsBar'), topZone = document.getElementById('ankiCardTopZone');
  const swipeZone = document.getElementById('ankiCardSwipeZone'), timerCont = document.getElementById('ankiTimerContainer');
  if (swipeZone) swipeZone.classList.remove('hidden');
  if (timerCont) timerCont.classList.remove('hidden');

  if (frontEl) frontEl.innerHTML = getFrontContent(card);
  applyFontSizes();

  if (!isFlipped) {
    if (backEl) backEl.classList.add('hidden');
    if (promptEl) promptEl.classList.remove('hidden');
    if (topZone) topZone.classList.add('my-auto');
    if (btnShow) btnShow.classList.remove('hidden');
    if (btnGroup) btnGroup.classList.add('hidden');
    if (swipeHints) swipeHints.classList.add('invisible');
  } else {
    if (backEl) backEl.classList.remove('hidden');
    if (promptEl) promptEl.classList.add('hidden');
    if (topZone) topZone.classList.remove('my-auto');
    if (readingEl && meaningEl) renderReadingsAndMeanings(card);
    if (notesEl) notesEl.innerHTML = card.notes || '';
    if (scrollEl) scrollEl.scrollTop = 0;
    if (btnShow) btnShow.classList.add('hidden');
    if (btnGroup) btnGroup.classList.remove('hidden');
    if (swipeHints) swipeHints.classList.remove('invisible');

    const ivls = card.intervals || { again: '<10m', good: '3g' };
    const setIvl = (id, val) => { const el = document.getElementById(id); if (el) el.innerText = val; };
    setIvl('ankiIvlWrong', ivls.again || '<10m');
    setIvl('ankiIvlCorrect', ivls.good || '3g');
  }
}

export function refreshCurrentCardView() {
  if (_activeCard) {
    const frontEl = document.getElementById('ankiCardFront');
    if (frontEl) frontEl.innerHTML = getFrontContent(_activeCard);
    applyFontSizes();
  }
}

export function showView(view) {
  const dList = document.getElementById('ankiDeckListView');
  const dOver = document.getElementById('ankiDeckOverviewView');
  const dStudy = document.getElementById('ankiStudyView');
  if (dList) dList.classList.toggle('hidden', view !== 'deckList');
  if (dOver) dOver.classList.toggle('hidden', view !== 'overview');
  if (dStudy) dStudy.classList.toggle('hidden', view !== 'study');
}

export function renderLearningCooldownWaiting(remainingSec, onLearnAhead, onExit) {
  const frontEl = document.getElementById('ankiCardFront');
  const backEl = document.getElementById('ankiCardBack');
  const promptEl = document.getElementById('ankiFlipPrompt');
  const btnShow = document.getElementById('ankiBtnShowAnswer');
  const btnGroup = document.getElementById('ankiAnswerButtonGroup');
  const swipeHints = document.getElementById('ankiSwipeHintsBar');

  if (backEl) backEl.classList.add('hidden');
  if (promptEl) promptEl.classList.add('hidden');
  if (btnGroup) btnGroup.classList.add('hidden');
  if (swipeHints) swipeHints.classList.add('hidden');

  const min = Math.floor(Math.max(0, remainingSec) / 60);
  const sec = Math.max(0, remainingSec) % 60;
  const timeStr = `${min}:${sec.toString().padStart(2, '0')}`;

  if (frontEl) {
    frontEl.innerHTML = `
      <div class="space-y-4 py-3 animate-info-fade select-none">
        <div class="text-4xl animate-pulse">⏳</div>
        <div class="text-base sm:text-lg font-bold text-white tracking-wide">In attesa del Cooldown</div>
        <div class="text-xs text-neutral-400 font-mono max-w-xs mx-auto leading-relaxed">
          Prossima carta rossa in apprendimento tra:
        </div>
        <div id="ankiCooldownDisplay" class="text-3xl font-mono font-bold text-[#EF5350] tracking-wider py-1">
          ${timeStr}
        </div>
        <div class="flex flex-col gap-2 max-w-xs mx-auto pt-2 pointer-events-auto">
          <button id="btnLearnAhead" class="w-full py-2.5 bg-[#EF5350]/20 hover:bg-[#EF5350]/30 active:scale-95 text-[#EF5350] border border-[#EF5350]/40 font-bold text-xs uppercase tracking-wider rounded-xl transition tap-press flex items-center justify-center gap-1.5 shadow-sm">
            <span>⚡ Ripassa Subito (Learn Ahead)</span>
          </button>
          <button id="btnCooldownExit" class="w-full py-2 bg-white/5 hover:bg-white/10 active:scale-95 text-neutral-400 font-mono text-xs rounded-xl transition tap-press">
            <span>Torna ai Mazzi ➔</span>
          </button>
        </div>
      </div>
    `;
    const btnAhead = document.getElementById('btnLearnAhead');
    if (btnAhead && onLearnAhead) btnAhead.onclick = onLearnAhead;
    const btnExit = document.getElementById('btnCooldownExit');
    if (btnExit && onExit) btnExit.onclick = onExit;
  }
  if (btnShow) btnShow.classList.add('hidden');
}

export function renderSessionFinished() {
  const frontEl = document.getElementById('ankiCardFront');
  const backEl = document.getElementById('ankiCardBack'), promptEl = document.getElementById('ankiFlipPrompt');
  const btnShow = document.getElementById('ankiBtnShowAnswer'), btnGroup = document.getElementById('ankiAnswerButtonGroup');
  const swipeHints = document.getElementById('ankiSwipeHintsBar'), swipeZone = document.getElementById('ankiCardSwipeZone');
  const timerCont = document.getElementById('ankiTimerContainer'), cardCont = document.getElementById('ankiCardContainer');
  const topZone = document.getElementById('ankiCardTopZone');

  if (cardCont) { cardCont.style.transition = 'none'; cardCont.style.transform = 'translate3d(0, 0, 0) scale(1) rotate(0deg)'; cardCont.style.opacity = '1'; }
  if (swipeZone) swipeZone.classList.add('hidden');
  if (timerCont) timerCont.classList.add('hidden');
  if (topZone) { topZone.classList.add('my-auto'); topZone.classList.remove('pt-2'); }
  if (backEl) backEl.classList.add('hidden');
  if (promptEl) promptEl.classList.add('hidden');
  if (btnGroup) btnGroup.classList.add('hidden');
  if (swipeHints) swipeHints.classList.add('hidden');

  if (frontEl) {
    frontEl.style.fontSize = '';
    frontEl.innerHTML = `
      <div class="space-y-4 py-4 animate-info-fade">
        <div class="text-5xl">🎉</div>
        <div class="text-xl sm:text-2xl font-bold text-white tracking-wide">Mazzo Completato!</div>
        <div class="text-xs sm:text-sm text-neutral-400 font-mono max-w-xs mx-auto leading-relaxed">
          Tutti i ripassi e le nuove carte per questo mazzo sono terminati per oggi.
        </div>
        <div class="pt-3">
          <button onclick="window.ankiShowDeckList()" class="px-8 py-3 bg-[#2196F3] hover:bg-[#1E88E5] text-white font-bold text-xs uppercase tracking-wider rounded-xl shadow-lg transition tap-press active:scale-95 flex items-center justify-center gap-2 mx-auto">
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
