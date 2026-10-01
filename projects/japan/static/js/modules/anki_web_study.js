// static/js/modules/anki_web_study.js — AnkiDroid Study Card Renderer (Zero-Lag Flip)
// Strictly <= 200 lines, <= 100 cols invariant.

import { triggerProgrammaticSwipe } from './anki_web_gestures.js';
import { applyFontSizes, getFuriganaMode } from './anki_web_settings.js';
import { renderReadingsAndMeanings } from './anki_web_meanings.js';
import { getCardRuleHintHtml } from './anki_card_rule_hints.js';
export {
  renderLearningCooldownWaiting,
  renderSessionFinished
} from './anki_study_status_views.js';
export { triggerProgrammaticSwipe };

let _activeCard = null;
let _isFlipped = false;
let _currentDeck = null;

const get = (id) => document.getElementById(id);

export function setCurrentDeck(deckOrId, name = '') {
  if (!deckOrId) {
    _currentDeck = null;
    return;
  }
  if (typeof deckOrId === 'object') {
    _currentDeck = { ...deckOrId };
  } else {
    _currentDeck = { id: Number(deckOrId), name, display_name: name };
  }
}

export const getSelectedDeck = () => _currentDeck;
export const getActiveCard = () => _activeCard;

export function renderStudyHeader(counts, currentNum, total) {
  const cNew = get('ankiCountNew');
  const cLrn = get('ankiCountLrn');
  const cRev = get('ankiCountRev');
  if (cNew) cNew.innerText = counts.new ?? 0;
  if (cLrn) cLrn.innerText = counts.learning ?? 0;
  if (cRev) cRev.innerText = counts.review ?? 0;
}

export function getFrontContent(card) {
  if (!card) return '';
  const mode = getFuriganaMode();
  let content = (mode === 'always')
    ? (card.ruby_all || card.front)
    : ((mode === 'unstudied') ? (card.ruby_unstudied || card.front) : card.front);
  const hintHtml = getCardRuleHintHtml(card);
  return hintHtml ? `${content}${hintHtml}` : content;
}

export function setCardFlippedState(flipped) {
  _isFlipped = flipped;
  const backEl = get('ankiCardBack');
  const promptEl = get('ankiFlipPrompt');
  const btnShow = get('ankiBtnShowAnswer');
  const btnGroup = get('ankiAnswerButtonGroup');
  const swipeHints = get('ankiSwipeHintsBar');

  if (flipped) {
    if (_activeCard) {
      const readingEl = get('ankiCardReading');
      const meaningEl = get('ankiCardMeaning');
      if (readingEl && meaningEl && !readingEl.hasChildNodes()) {
        renderReadingsAndMeanings(_activeCard);
        const notesEl = get('ankiCardNotes');
        if (notesEl) notesEl.innerHTML = _activeCard.notes || '';
      }
    }
    if (backEl) backEl.classList.remove('hidden');
    if (promptEl) promptEl.classList.add('hidden');
    if (btnShow) btnShow.classList.add('hidden');
    if (btnGroup) btnGroup.classList.remove('hidden');
    if (swipeHints) swipeHints.classList.remove('invisible');
  } else {
    if (backEl) backEl.classList.add('hidden');
    if (promptEl) promptEl.classList.remove('hidden');
    if (btnShow) btnShow.classList.remove('hidden');
    if (btnGroup) btnGroup.classList.add('hidden');
    if (swipeHints) swipeHints.classList.add('invisible');
  }
}

export function renderCardContent(card) {
  if (!card) return;
  _activeCard = card;
  _isFlipped = false;

  const frontEl = get('ankiCardFront');
  const readingEl = get('ankiCardReading');
  const meaningEl = get('ankiCardMeaning');
  const notesEl = get('ankiCardNotes');
  const scrollEl = get('ankiCardMeaningScroll');

  get('ankiCardSwipeZone')?.classList.remove('hidden');
  get('ankiTimerContainer')?.classList.remove('hidden');

  // 1. Render front instantly (< 1ms)
  if (frontEl) frontEl.innerHTML = getFrontContent(card);

  const ivls = card.intervals || { again: '<10m', good: '3g' };
  const wrongEl = get('ankiIvlWrong');
  const corEl = get('ankiIvlCorrect');
  if (wrongEl) wrongEl.innerText = ivls.again || '<10m';
  if (corEl) corEl.innerText = ivls.good || '3g';

  applyFontSizes();

  // 2. Set initial unflipped visibility
  setCardFlippedState(false);

  // 3. Render back notes immediately and schedule reading parsing on next rAF
  if (notesEl) notesEl.innerHTML = card.notes || '';
  if (scrollEl) scrollEl.scrollTop = 0;
  if (readingEl && meaningEl) {
    readingEl.innerHTML = '';
    meaningEl.innerHTML = '';
    requestAnimationFrame(() => {
      if (_activeCard === card) renderReadingsAndMeanings(card);
    });
  }
}

export function updateCardElements(card, isFlipped) {
  if (!card) return;
  if (card !== _activeCard || !isFlipped) {
    renderCardContent(card);
    if (isFlipped) setCardFlippedState(true);
  } else {
    setCardFlippedState(isFlipped);
  }
}

export function refreshCurrentCardView() {
  if (_activeCard) {
    const frontEl = get('ankiCardFront');
    if (frontEl) frontEl.innerHTML = getFrontContent(_activeCard);
    applyFontSizes();
  }
}

export function showView(view) {
  const dList = get('ankiDeckListView');
  const dOver = get('ankiDeckOverviewView');
  const dStudy = get('ankiStudyView');
  if (dList) dList.classList.toggle('hidden', view !== 'deckList');
  if (dOver) dOver.classList.toggle('hidden', view !== 'overview');
  if (dStudy) dStudy.classList.toggle('hidden', view !== 'study');
}
