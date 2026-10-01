// static/js/modules/anki_web_fatigue.js — Cognitive Anti-Fatigue Monitor & Micro-Break Engine
// Strictly <= 200 lines invariant.

import { pauseSessionTimer, resumeSessionTimer, getSessionStats } from './anki_web_session_timer.js';
import { pauseCardTimer, startCardTimer } from './anki_web_timer.js';

let _reviewHistory = []; // { timeMs: number, grade: number }
let _fatigueDismissedAt = 0;
let _breakInterval = null, _breakRemainSec = 120;
let _sessionWasRunningBeforeBreak = false;

const get = id => document.getElementById(id);

export function resetFatigueTracker() {
  _reviewHistory = [];
  _fatigueDismissedAt = 0;
  _sessionWasRunningBeforeBreak = false;
  hideFatigueModal();
  stopMicroBreak();
}

export function recordReviewForFatigue(timeMs, grade, durationSec = 0) {
  // Untimed guard: strictly disable fatigue tracking on untimed / stopwatch cards
  if (!durationSec || durationSec <= 0) return;

  const timeSec = timeMs / 1000.0;
  const timeRatio = Math.max(0.05, Math.min(2.0, timeSec / durationSec));

  _reviewHistory.push({ timeMs: Math.max(200, timeMs), grade, durationSec, timeRatio });
  if (_reviewHistory.length < 20) return; // Need minimal warm-up sample
  if (Date.now() - _fatigueDismissedAt < 5 * 60 * 1000) return; // 5 min cooldown

  const baselineSlice = _reviewHistory.slice(0, 10);
  const recentSlice = _reviewHistory.slice(-5);

  const avgBaselineRatio = baselineSlice.reduce((a, b) => a + b.timeRatio, 0) / baselineSlice.length;
  const avgRecentRatio = recentSlice.reduce((a, b) => a + b.timeRatio, 0) / recentSlice.length;
  const slowdownRatio = (avgRecentRatio - avgBaselineRatio) / Math.max(0.1, avgBaselineRatio);

  const recentLapses = recentSlice.filter(r => r.grade === 1).length;
  const isFatigued = (slowdownRatio >= 0.50 && avgRecentRatio >= 0.75) || (recentLapses >= 3 && _reviewHistory.length >= 25);

  if (isFatigued) {
    showFatigueModal(Math.round(slowdownRatio * 100), recentLapses, Math.round(avgRecentRatio * 100));
  }
}

export function showFatigueModal(slowdownPct, recentLapses, avgRecentRatioPct = 0) {
  const modal = get('ankiFatigueModal');
  const msgEl = get('ankiFatigueMsg');
  if (!modal) return;

  if (msgEl) {
    if (recentLapses >= 3) {
      msgEl.innerText = `Rilevati 3 errori consecutivi su ${_reviewHistory.length} carte a tempo. Il calo di attenzione rischia di degradare la qualità della memoria FSRS.`;
    } else {
      msgEl.innerText = `Il tempo impiegato per rispondere è salito al ${avgRecentRatioPct}% del limite (+${Math.max(30, slowdownPct)}% rispetto all'inizio). Una micro-pausa previene il burnout.`;
    }
  }
  modal.classList.remove('hidden');
}

export function hideFatigueModal() {
  const modal = get('ankiFatigueModal');
  if (modal) modal.classList.add('hidden');
  _fatigueDismissedAt = Date.now();
}

export function startMicroBreak(seconds = 120) {
  hideFatigueModal();
  const breakModal = get('ankiBreakModal');
  if (!breakModal) return;

  // 1. Pause top session timer so the 2-min break is not counted as study time
  const stats = getSessionStats();
  _sessionWasRunningBeforeBreak = !!stats.isRunning;
  if (_sessionWasRunningBeforeBreak) {
    pauseSessionTimer();
  }
  pauseCardTimer();

  // 2. Setup Stages: Show active countdown stage, hide finished stage
  const activeStage = get('ankiBreakActiveStage');
  const finishedStage = get('ankiBreakFinishedStage');
  if (activeStage) activeStage.classList.remove('hidden');
  if (finishedStage) finishedStage.classList.add('hidden');

  breakModal.classList.remove('hidden');

  _breakRemainSec = seconds;
  updateBreakUI();

  if (_breakInterval) clearInterval(_breakInterval);
  _breakInterval = setInterval(() => {
    _breakRemainSec--;
    updateBreakUI();
    if (_breakRemainSec <= 0) {
      onBreakCountdownCompleted();
    }
  }, 1000);
}

function onBreakCountdownCompleted() {
  if (_breakInterval) { clearInterval(_breakInterval); _breakInterval = null; }
  playBreakFinishedSound();

  const activeStage = get('ankiBreakActiveStage');
  const finishedStage = get('ankiBreakFinishedStage');
  if (activeStage) activeStage.classList.add('hidden');
  if (finishedStage) finishedStage.classList.remove('hidden');
}

export function stopMicroBreak() {
  if (_breakInterval) { clearInterval(_breakInterval); _breakInterval = null; }
  const breakModal = get('ankiBreakModal');
  if (breakModal) breakModal.classList.add('hidden');

  // Reset stage classes for next time
  const activeStage = get('ankiBreakActiveStage');
  const finishedStage = get('ankiBreakFinishedStage');
  if (activeStage) activeStage.classList.remove('hidden');
  if (finishedStage) finishedStage.classList.add('hidden');

  // Resume top session timer if it was running before the break
  if (_sessionWasRunningBeforeBreak) {
    resumeSessionTimer();
    _sessionWasRunningBeforeBreak = false;
  }

  // Resume card timer for active card
  if (typeof window !== 'undefined' && window.ankiGetCurrentCard) {
    const card = window.ankiGetCurrentCard();
    if (card) startCardTimer(card);
  }
}

function playBreakFinishedSound() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const now = ctx.currentTime;
    // Pleasant restorative triad (E5 659Hz, G#5 831Hz, B5 988Hz)
    [659.25, 830.61, 987.77].forEach((freq, idx) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, now + idx * 0.09);
      gain.gain.setValueAtTime(0.001, now + idx * 0.09);
      gain.gain.exponentialRampToValueAtTime(0.12, now + idx * 0.09 + 0.05);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + idx * 0.09 + 1.8);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now + idx * 0.09);
      osc.stop(now + idx * 0.09 + 1.8);
    });
  } catch {}
  if ('vibrate' in navigator) {
    try { navigator.vibrate([150, 100, 200]); } catch {}
  }
}

function updateBreakUI() {
  const textEl = get('ankiBreakTimerText');
  const circleEl = get('ankiBreakCircle');
  if (textEl) {
    const m = Math.floor(_breakRemainSec / 60), s = _breakRemainSec % 60;
    textEl.innerText = `${m}:${String(s).padStart(2, '0')}`;
  }
  if (circleEl) {
    // Breathing expansion guide: 4s inhale, 4s hold, 4s exhale
    const cycle = _breakRemainSec % 12;
    if (cycle >= 8) circleEl.className = 'w-28 h-28 rounded-full bg-[#42A5F5]/30 border-2 border-[#42A5F5] flex items-center justify-center transition-all duration-1000 transform scale-110 shadow-lg';
    else if (cycle >= 4) circleEl.className = 'w-28 h-28 rounded-full bg-[#66BB6A]/30 border-2 border-[#66BB6A] flex items-center justify-center transition-all duration-1000 transform scale-100 shadow-lg';
    else circleEl.className = 'w-28 h-28 rounded-full bg-[#FFA726]/30 border-2 border-[#FFA726] flex items-center justify-center transition-all duration-1000 transform scale-90 shadow-lg';
  }
}

