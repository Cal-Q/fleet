// static/js/modules/anki_web_session_timer.js — Session Target & Card Timer Coordination
// Strictly <= 200 lines invariant.

import {
  openSessionTimerModal as openModalImpl, closeSessionTimerModal as closeModalImpl,
  switchTimerTab as switchTabImpl, updateModalTimerUI as updateModalUIImpl,
  updateSessionTimerUI as updateTimerUIImpl
} from './anki_web_session_timer_ui.js';
import { setCurrentDeck, getCurrentDeckInfo, getTimerDuration, setTimerDuration, applyTimerToAllDecks } from './anki_web_timer.js';

let _sessionTargetMin = 0, _sessionElapsedSec = 0, _sessionStartTime = 0;
let _sessionTimerInterval = null, _isSessionRunning = false, _isCompleted = false;

function getState() {
  return {
    targetMin: _sessionTargetMin, elapsedSec: _sessionElapsedSec,
    isRunning: _isSessionRunning, isCompleted: _isCompleted
  };
}

export function initSessionTimer() {
  const saved = localStorage.getItem('anki_session_target_min');
  if (saved !== null) _sessionTargetMin = parseInt(saved, 10) || 0;
  updateTimerUIImpl(getState());
}

export function startSessionTimer() {
  _sessionStartTime = Date.now() - (_sessionElapsedSec * 1000);
  _isSessionRunning = true;
  _isCompleted = false;
  if (_sessionTimerInterval) clearInterval(_sessionTimerInterval);

  syncUI();
  _sessionTimerInterval = setInterval(() => {
    _sessionElapsedSec = Math.floor((Date.now() - _sessionStartTime) / 1000);
    syncUI();
    if (_sessionTargetMin > 0 && _sessionElapsedSec >= _sessionTargetMin * 60) {
      onSessionTimerCompleted();
    }
  }, 1000);
}

export function pauseSessionTimer() {
  _isSessionRunning = false;
  if (_sessionTimerInterval) {
    clearInterval(_sessionTimerInterval);
    _sessionTimerInterval = null;
  }
  syncUI();
}

export function resumeSessionTimer() {
  if (!_isSessionRunning) {
    startSessionTimer();
  }
}

export function togglePauseSessionTimer() {
  if (_isCompleted) { restartSessionTimer(); return; }
  if (_isSessionRunning) pauseSessionTimer();
  else resumeSessionTimer();
}

export function resetSessionTimer() {
  pauseSessionTimer();
  _sessionElapsedSec = 0;
  _sessionStartTime = Date.now();
  _isCompleted = false;
  syncUI();
}

export function restartSessionTimer() {
  resetSessionTimer();
  startSessionTimer();
}

export function setSessionTargetMin(minutes) {
  _sessionTargetMin = Math.max(0, Math.min(180, parseInt(minutes, 10) || 0));
  localStorage.setItem('anki_session_target_min', _sessionTargetMin);
  _isCompleted = false;
  syncUI();
}

export function adjustSessionCustomMin(delta) {
  setSessionTargetMin(_sessionTargetMin + delta);
}

export function setCardTimerPreset(seconds) {
  setTimerDuration(seconds);
  syncUI();
}

export function openSessionTimerModal(initialTab = 'session') {
  openModalImpl(getState(), getCurrentDeckInfo(), initialTab);
}

export function openCardTimerModal(did = null, name = '') {
  if (did !== null && did !== undefined) {
    setCurrentDeck(did, name);
  }
  openSessionTimerModal('card');
}

export function closeSessionTimerModal() {
  closeModalImpl();
}

export function switchTimerTab(tab) {
  switchTabImpl(tab);
  syncUI();
}

export function getSessionStats() {
  return getState();
}

function syncUI() {
  const st = getState();
  updateTimerUIImpl(st);
  updateModalUIImpl(st, getCurrentDeckInfo());
}

function onSessionTimerCompleted() {
  pauseSessionTimer();
  _isCompleted = true;
  playChime();
  if ('vibrate' in navigator) navigator.vibrate([100, 50, 100, 50, 200]);
  syncUI();
}

function playChime() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator(), gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(587.33, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(880.00, ctx.currentTime + 0.3);
    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.6);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.6);
  } catch {}
}

Object.assign(window, {
  ankiOpenSessionTimerModal: () => openSessionTimerModal('session'),
  ankiOpenCardTimerModal: openCardTimerModal,
  ankiCloseSessionTimerModal: closeSessionTimerModal,
  ankiSwitchTimerTab: switchTimerTab,
  ankiRestartSessionTimer: restartSessionTimer,
  ankiTogglePauseSessionTimer: togglePauseSessionTimer,
  ankiSetSessionPreset: setSessionTargetMin,
  ankiAdjustSessionCustomMin: adjustSessionCustomMin,
  ankiSetSessionCustomMin: (v) => setSessionTargetMin(parseInt(v, 10) || 0),
  ankiSetCardTimerPreset: setCardTimerPreset,
  ankiApplyTimerToAllDecks: () => { applyTimerToAllDecks(); syncUI(); }
});
