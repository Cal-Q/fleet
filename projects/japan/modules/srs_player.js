// static/js/modules/srs_player.js — SRS Interactive Card Player Orchestration
// Strictly <= 200 lines invariant.

import { renderLoading, renderEmpty, renderCardView, renderCompletion } from './srs_player_render.js';

let _cards = [];
let _currentIndex = 0;
let _isFlipped = false;
let _deckCounts = { new: 0, learning: 0, review: 0 };

export async function initSrsPlayer() {
  const container = document.getElementById('srsPlayerRoot');
  if (!container) return;

  setupKeyboardShortcuts();
  await loadDemoCards();
}

export async function loadDemoCards() {
  const container = document.getElementById('srsPlayerRoot');
  if (!container) return;

  try {
    renderLoading(container);
    const res = await fetch('/api/srs/demo_cards');
    const data = await res.json();

    if (data.status === 'ok' && data.cards?.length > 0) {
      _cards = data.cards;
      _deckCounts = data.counts || { new: 0, learning: 0, review: 0 };
      _currentIndex = 0;
      _isFlipped = false;
      updateUI();
    } else {
      renderEmpty(container, 'Nessuna carta disponibile al momento.');
    }
  } catch (err) {
    renderEmpty(container, 'Errore caricamento: ' + err.message);
  }
}

export function flipCard() {
  if (_isFlipped) return;
  _isFlipped = true;
  updateUI();
}

export function answerCard(grade) {
  if (!_cards[_currentIndex]) return;
  _currentIndex++;
  _isFlipped = false;

  const container = document.getElementById('srsPlayerRoot');
  if (_currentIndex >= _cards.length) {
    renderCompletion(container, () => loadDemoCards());
  } else {
    updateUI();
  }
}

function updateUI() {
  const container = document.getElementById('srsPlayerRoot');
  if (!container) return;
  const card = _cards[_currentIndex];
  renderCardView(container, card, _isFlipped, _deckCounts, _currentIndex + 1, _cards.length);
}

function setupKeyboardShortcuts() {
  window.removeEventListener('keydown', handleGlobalKeydown);
  window.addEventListener('keydown', handleGlobalKeydown);
}

function handleGlobalKeydown(e) {
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName) || document.activeElement?.isContentEditable) return;
  if (typeof window.getActiveStage === 'function' && window.getActiveStage() !== 'bunki') return;
  const player = document.getElementById('srsPlayerRoot');
  if (!player || player.offsetParent === null) return;

  if (e.code === 'Space' || e.key === 'Enter') {
    e.preventDefault();
    if (!_isFlipped) {
      flipCard();
    } else {
      answerCard(3);
    }
  } else if (_isFlipped) {
    if (e.key === '1') { e.preventDefault(); answerCard(1); }
    else if (e.key === '2') { e.preventDefault(); answerCard(2); }
    else if (e.key === '3') { e.preventDefault(); answerCard(3); }
    else if (e.key === '4') { e.preventDefault(); answerCard(4); }
  }
}

// Global window bindings for onclick
window.srsFlipCard = flipCard;
window.srsAnswerCard = answerCard;
window.initSrsPlayer = initSrsPlayer;
