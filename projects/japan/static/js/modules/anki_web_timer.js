// static/js/modules/anki_web_timer.js
// Core Card Study Countdown & Interval Coordinator (<= 200 lines, <= 100 cols)
import { ankiLog } from './anki_logger.js';
import { persistSetting } from './anki_web_persistence.js';
import {
  resetTimerRenderState, showTimerBar, bounceTimerText,
  updateTimerUI, onTimerExpiredUI, updateTimerSettingsUI
} from './anki_timer_render.js';

const DEFAULT_TIMER_SEC = 15;

export function loadStoredDeckTimers() {
  try {
    const initT = (typeof window !== 'undefined')
      ? window.__INITIAL_SETTINGS__?.deck_timers : null;
    const raw = (typeof localStorage !== 'undefined')
      ? localStorage.getItem('anki_deck_timers') : null;
    const parsed = raw ? JSON.parse(raw) : null;
    return { ...(initT || {}), ...(parsed || {}) };
  } catch {
    return {};
  }
}

let _deckTimers = loadStoredDeckTimers();
let _currentDeckId = null;
let _currentDeckName = '';
let _durationSec = DEFAULT_TIMER_SEC;
let _startTime = 0;
let _elapsedMs = 0;
let _timerInterval = null;
let _isTimerRunning = false;
let _pauseTimerUI = false;

const get = (id) => document.getElementById(id);

export function initCardTimer() {
  _deckTimers = loadStoredDeckTimers();
  updateActiveDuration();
}

export function setCurrentDeck(did, name) {
  _currentDeckId = did ? String(did) : null;
  _currentDeckName = name || '';
  if (!_deckTimers || Object.keys(_deckTimers).length === 0) {
    _deckTimers = loadStoredDeckTimers();
  }
  updateActiveDuration();
}

export const getCurrentDeckInfo = () => (
  { id: _currentDeckId, name: _currentDeckName, duration: _durationSec }
);

function updateActiveDuration() {
  if (_currentDeckId && _deckTimers[_currentDeckId] !== undefined) {
    _durationSec = parseInt(_deckTimers[_currentDeckId], 10) || 0;
  } else {
    const initD = window.__INITIAL_SETTINGS__?.timer_duration ?? DEFAULT_TIMER_SEC;
    const glob = (typeof localStorage !== 'undefined')
      ? localStorage.getItem('anki_timer_duration') : null;
    _durationSec = glob !== null ? (parseInt(glob, 10) || 0) : initD;
  }
  updateTimerSettingsUI(_durationSec, _currentDeckName);
}

function getCardDeckId(card) {
  if (!card) return null;
  const directId = card.did || card.deck_id;
  if (directId) return String(directId);
  const decks = window.__INITIAL_DECKS__;
  if (card.deck_name && Array.isArray(decks)) {
    const f = decks.find((d) => d.name === card.deck_name);
    return f ? String(f.id) : null;
  }
  return null;
}

export function getCardTimerDuration(card) {
  if (!card) return _durationSec;
  const cDid = getCardDeckId(card);
  if (cDid) {
    if (_deckTimers[cDid] !== undefined) {
      return parseInt(_deckTimers[cDid], 10) || 0;
    }
    const fresh = loadStoredDeckTimers();
    if (fresh[cDid] !== undefined) {
      _deckTimers = fresh;
      return parseInt(fresh[cDid], 10) || 0;
    }
  }
  const glob = typeof localStorage !== 'undefined'
    ? localStorage.getItem('anki_timer_duration') : null;
  return glob !== null ? (parseInt(glob, 10) || 0) : (_durationSec || DEFAULT_TIMER_SEC);
}

export function startCardTimer(card = null) {
  stopCardTimer();
  if (card) {
    const cDid = getCardDeckId(card);
    if (cDid) {
      _currentDeckId = cDid;
      _currentDeckName = card.deck_name || '';
    }
    _durationSec = getCardTimerDuration(card);
  }
  restartCardTimer();
}

function clearTimerInterval() {
  if (_timerInterval) {
    clearInterval(_timerInterval);
  }
  _timerInterval = null;
}

export function pauseCardTimer() {
  clearTimerInterval();
  if (_isTimerRunning) {
    _elapsedMs = Date.now() - _startTime;
  }
  _isTimerRunning = false;
  return _elapsedMs;
}

export function stopCardTimer() {
  pauseCardTimer();
  _elapsedMs = 0;
}

export function restartCardTimer() {
  clearTimerInterval();
  _startTime = Date.now();
  _elapsedMs = 0;
  _isTimerRunning = true;
  resetTimerRenderState();
  const progressEl = get('ankiTimerProgress');
  if (progressEl) {
    progressEl.style.transition = 'none';
    progressEl.style.transform = 'scaleX(1)';
  }
  showTimerBar();
  updateTimerUI(_durationSec, _elapsedMs);
  _timerInterval = setInterval(() => {
    _elapsedMs = Date.now() - _startTime;
    if (!_pauseTimerUI) {
      updateTimerUI(_durationSec, _elapsedMs);
      if (_durationSec > 0 && _elapsedMs >= _durationSec * 1000) {
        onTimerExpiredUI();
      }
    }
  }, 100);
  bounceTimerText();
}

export function setTimerUIPaused(paused) {
  _pauseTimerUI = !!paused;
  if (!_pauseTimerUI && _isTimerRunning) {
    updateTimerUI(_durationSec, Date.now() - _startTime);
  }
}

export const getElapsedMs = () => (
  _isTimerRunning ? (Date.now() - _startTime) : _elapsedMs
);

export function getTimerRemainingRatio() {
  if (!_durationSec || _durationSec <= 0) return 1.0;
  return Math.max(0, 1.0 - (getElapsedMs() / (_durationSec * 1000.0)));
}

export function setTimerDuration(seconds) {
  _durationSec = Math.max(0, Math.min(60, parseInt(seconds, 10) || 0));
  if (_currentDeckId) {
    _deckTimers[_currentDeckId] = _durationSec;
    persistSetting('anki_deck_timers', _deckTimers);
    ankiLog('ACTION', 'SETTINGS', 'SET_DECK_TIMER', {
      did: _currentDeckId, deck: _currentDeckName, sec: _durationSec
    });
  } else {
    persistSetting('anki_timer_duration', _durationSec);
    ankiLog('ACTION', 'SETTINGS', 'SET_GLOBAL_TIMER', { sec: _durationSec });
  }
  updateTimerSettingsUI(_durationSec, _currentDeckName);
  if (_isTimerRunning) startCardTimer();
}

export function applyTimerToAllDecks(seconds = null) {
  if (seconds !== null) {
    _durationSec = Math.max(0, Math.min(60, parseInt(seconds, 10) || 0));
  }
  _deckTimers = {};
  persistSetting('anki_timer_duration', _durationSec);
  persistSetting('anki_deck_timers', _deckTimers);
  updateTimerSettingsUI(_durationSec, _currentDeckName);
  if (_isTimerRunning) startCardTimer();
  ankiLog('ACTION', 'SETTINGS', 'APPLY_TIMER_ALL_DECKS', { sec: _durationSec });
}

export const getTimerDuration = () => _durationSec;
