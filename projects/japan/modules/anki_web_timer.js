import { ankiLog } from './anki_logger.js';
import { persistSetting } from './anki_web_persistence.js';

const DEFAULT_TIMER_SEC = 15;

export function loadStoredDeckTimers() {
  let timers = {};
  try {
    const initT = (typeof window !== 'undefined' && window.__INITIAL_SETTINGS__?.deck_timers);
    if (initT && typeof initT === 'object') timers = { ...initT };
    const raw = typeof localStorage !== 'undefined' ? localStorage.getItem('anki_deck_timers') : null;
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === 'object' && Object.keys(parsed).length > 0) timers = { ...timers, ...parsed };
    }
  } catch {}
  return timers;
}

let _deckTimers = loadStoredDeckTimers(), _currentDeckId = null, _currentDeckName = '';
let _durationSec = DEFAULT_TIMER_SEC;
let _startTime = 0, _elapsedMs = 0, _timerInterval = null, _isTimerRunning = false;

const get = id => document.getElementById(id);

export function initCardTimer() {
  _deckTimers = loadStoredDeckTimers();
  updateActiveDuration();
}

export function setCurrentDeck(did, name) {
  _currentDeckId = did ? String(did) : null;
  _currentDeckName = name || '';
  if (!_deckTimers || Object.keys(_deckTimers).length === 0) _deckTimers = loadStoredDeckTimers();
  updateActiveDuration();
}

export function getCurrentDeckInfo() {
  return { id: _currentDeckId, name: _currentDeckName, duration: _durationSec };
}

function updateActiveDuration() {
  if (_currentDeckId && _deckTimers[_currentDeckId] !== undefined) {
    _durationSec = parseInt(_deckTimers[_currentDeckId], 10) || 0;
  } else {
    const initD = (typeof window !== 'undefined' && window.__INITIAL_SETTINGS__?.timer_duration !== undefined) ? window.__INITIAL_SETTINGS__.timer_duration : DEFAULT_TIMER_SEC;
    const glob = localStorage.getItem('anki_timer_duration');
    _durationSec = glob !== null ? (parseInt(glob, 10) || 0) : initD;
  }
  updateTimerSettingsUI();
}

function getCardDeckId(card) {
  if (!card) return null;
  if (card.did) return String(card.did);
  if (card.deck_id) return String(card.deck_id);
  if (card.deck_name && Array.isArray(window.__INITIAL_DECKS__)) {
    const f = window.__INITIAL_DECKS__.find(d => d.name === card.deck_name);
    if (f) return String(f.id);
  }
  return null;
}

export function getCardTimerDuration(card) {
  if (!card) return _durationSec;
  const cDid = getCardDeckId(card);
  if (cDid) {
    if (_deckTimers[cDid] !== undefined) return parseInt(_deckTimers[cDid], 10) || 0;
    const fresh = loadStoredDeckTimers();
    if (fresh[cDid] !== undefined) { _deckTimers = fresh; return parseInt(fresh[cDid], 10) || 0; }
  }
  const glob = localStorage.getItem('anki_timer_duration');
  return glob !== null ? (parseInt(glob, 10) || 0) : (_durationSec || DEFAULT_TIMER_SEC);
}

export function startCardTimer(card = null) {
  stopCardTimer();
  if (card) {
    const cDid = getCardDeckId(card);
    if (cDid) { _currentDeckId = cDid; _currentDeckName = card.deck_name || ''; }
    _durationSec = getCardTimerDuration(card);
  }
  _startTime = Date.now(); _elapsedMs = 0; _isTimerRunning = true;
  _lastRemainSec = -1; _lastPhase = '';
  const progressEl = get('ankiTimerProgress');
  if (progressEl) { progressEl.style.transition = 'none'; progressEl.style.transform = 'scaleX(1)'; }
  showTimerBar(); updateTimerUI();
  _timerInterval = setInterval(() => {
    _elapsedMs = Date.now() - _startTime;
    updateTimerUI();
    if (_durationSec > 0 && _elapsedMs >= _durationSec * 1000) onTimerExpired();
  }, 100);
}

export function pauseCardTimer() {
  if (_timerInterval) { clearInterval(_timerInterval); _timerInterval = null; }
  if (_isTimerRunning) _elapsedMs = Date.now() - _startTime;
  _isTimerRunning = false;
  return _elapsedMs;
}

export function stopCardTimer() { pauseCardTimer(); _elapsedMs = 0; }

export function restartCardTimer() {
  _startTime = Date.now(); _elapsedMs = 0; _isTimerRunning = true;
  _lastRemainSec = -1; _lastPhase = '';
  const progressEl = get('ankiTimerProgress');
  if (progressEl) { progressEl.style.transition = 'none'; progressEl.style.transform = 'scaleX(1)'; }
  updateTimerUI();
  const textEl = get('ankiTimerText');
  if (textEl) {
    textEl.style.transform = 'scale(1.25)';
    setTimeout(() => { if (textEl) textEl.style.transform = 'scale(1)'; }, 150);
  }
}

export function getElapsedMs() { return _isTimerRunning ? (Date.now() - _startTime) : _elapsedMs; }

export function setTimerDuration(seconds) {
  _durationSec = Math.max(0, Math.min(60, parseInt(seconds, 10) || 0));
  if (_currentDeckId) {
    _deckTimers[_currentDeckId] = _durationSec;
    persistSetting('anki_deck_timers', _deckTimers);
    ankiLog('ACTION', 'SETTINGS', 'SET_DECK_TIMER', { did: _currentDeckId, deck: _currentDeckName, sec: _durationSec });
  } else {
    persistSetting('anki_timer_duration', _durationSec);
    ankiLog('ACTION', 'SETTINGS', 'SET_GLOBAL_TIMER', { sec: _durationSec });
  }
  updateTimerSettingsUI();
  if (_isTimerRunning) startCardTimer();
}

export function applyTimerToAllDecks(seconds = null) {
  if (seconds !== null) _durationSec = Math.max(0, Math.min(60, parseInt(seconds, 10) || 0));
  persistSetting('anki_timer_duration', _durationSec);
  _deckTimers = {};
  persistSetting('anki_deck_timers', _deckTimers);
  updateTimerSettingsUI();
  if (_isTimerRunning) startCardTimer();
  ankiLog('ACTION', 'SETTINGS', 'APPLY_TIMER_ALL_DECKS', { sec: _durationSec });
}

export function getTimerDuration() { return _durationSec; }
function showTimerBar() { const bar = get('ankiTimerContainer'); if (bar) bar.classList.remove('hidden'); }
function formatTime(sec) { const m = Math.floor(sec / 60), s = sec % 60; return m > 0 ? `${m}:${String(s).padStart(2, '0')}` : `${s}s`; }

let _lastRemainSec = -1, _lastPhase = '';

function updateTimerUI() {
  const progressEl = get('ankiTimerProgress'), textEl = get('ankiTimerText'), iconEl = get('ankiTimerIcon');
  if (!progressEl || !textEl) return;
  if (_durationSec <= 0) {
    const s = Math.floor(_elapsedMs / 1000);
    if (s !== _lastRemainSec) {
      _lastRemainSec = s;
      textEl.innerText = formatTime(s);
      textEl.className = 'font-bold text-[#42A5F5] w-12 text-right flex-shrink-0 text-[11px]';
      if (iconEl) iconEl.innerText = '⏱️';
      progressEl.style.transition = 'none';
      progressEl.style.transform = 'scaleX(1)';
      progressEl.className = 'h-full w-full rounded-full bg-[#42A5F5]/40 origin-left animate-pulse';
    }
    return;
  }
  const totalMs = _durationSec * 1000, remainMs = Math.max(0, totalMs - _elapsedMs);
  const remainSec = Math.ceil(remainMs / 1000), fraction = Math.max(0, Math.min(1, remainMs / totalMs));
  if (_elapsedMs > 0) progressEl.style.transition = 'transform 0.1s linear';
  progressEl.style.transform = `scaleX(${fraction})`;
  const pct = fraction * 100;
  const phase = pct > 50 ? 'good' : (pct > 25 ? 'warn' : 'danger');
  if (remainSec !== _lastRemainSec || phase !== _lastPhase) {
    _lastRemainSec = remainSec; _lastPhase = phase;
    textEl.innerText = `${remainSec}s`;
    if (iconEl) iconEl.innerText = '⏳';
    const bgCol = phase === 'good' ? 'bg-[#66BB6A]' : (phase === 'warn' ? 'bg-[#FFA726]' : 'bg-[#EF5350]');
    progressEl.className = `h-full w-full rounded-full ${bgCol} origin-left`;
    textEl.className = `font-bold ${phase === 'good' ? 'text-white' : (phase === 'warn' ? 'text-[#FFA726]' : 'text-[#EF5350]')} w-12 text-right flex-shrink-0 text-[11px]`;
  }
}

function onTimerExpired() {
  const textEl = get('ankiTimerText');
  if (textEl) { textEl.innerText = '0s'; textEl.classList.add('animate-pulse', 'text-[#EF5350]'); }
}

export function updateTimerSettingsUI() {
  const slider = get('sliderTimerDuration'), label = get('labelTimerDuration'), deckLabel = get('labelTimerDeckTarget');
  if (slider) slider.value = _durationSec;
  if (label) {
    label.innerText = _durationSec > 0 ? `${_durationSec}s` : 'Cronometro (Libero)';
    label.className = _durationSec > 0 ? 'font-bold text-[#FFA726]' : 'font-bold text-[#42A5F5]';
  }
  if (deckLabel) deckLabel.innerText = `Mazzo: ${_currentDeckName ? _currentDeckName.split('::').pop() : 'Tutti i Mazzi'}`;
}
