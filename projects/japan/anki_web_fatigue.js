// static/js/modules/anki_web_fatigue.js — Cognitive Anti-Fatigue Monitor & Neural Micro-Break Engine
// TPU Tabula Rasa model integration. Strictly <= 200 lines invariant.

import { pauseSessionTimer, resumeSessionTimer, getSessionStats } from './anki_web_session_timer.js';
import { pauseCardTimer, startCardTimer } from './anki_web_timer.js';
import { loadNeuralWeights, forwardCognitiveState, evaluateOptimalPause, projectRecovery, extractTelemetryVector, recordPersistentReviewRatio } from './anki_fatigue_neural.js';
import { startFatigueEvaluation, recordReviewForEvaluation } from './anki_fatigue_eval.js';
import { captureFatiguePromptSnapshot, buildDebugModalHtml } from './anki_fatigue_snapshot.js';

let _reviewHistory = [], _fatigueDismissedAt = 0, _lastBreakCompletedAt = 0;
let _breakInterval = null, _breakRemainSec = 60, _currentRecSec = 60, _breakTotalSec = 60;
let _sessionWasRunningBeforeBreak = false, _currentRecData = null;
let _currentCognitiveZ = null, _postBreakBaselineLapseRisk = null;
const get = id => document.getElementById(id);

export function resetFatigueTracker() {
  _reviewHistory = []; _fatigueDismissedAt = 0; _lastBreakCompletedAt = 0;
  _currentCognitiveZ = null; _postBreakBaselineLapseRisk = null;
  _sessionWasRunningBeforeBreak = false; _currentRecData = null;
  if (_breakInterval) { clearInterval(_breakInterval); _breakInterval = null; }
  const fm = get('ankiFatigueModal'), bm = get('ankiBreakModal');
  if (fm) fm.classList.add('hidden');
  if (bm) bm.classList.add('hidden');
}

export async function recordReviewForFatigue(cardOrTime, timeMsOrGrade, gradeOrDuration = 0, maybeDuration = 0) {
  let card = null, timeMs = 1000, grade = 3, durationSec = 0;
  if (typeof cardOrTime === 'object' && cardOrTime !== null) { card = cardOrTime; timeMs = timeMsOrGrade; grade = gradeOrDuration; durationSec = maybeDuration; }
  else { timeMs = cardOrTime; grade = timeMsOrGrade; durationSec = gradeOrDuration; }

  const dur = (durationSec && durationSec > 0) ? durationSec : 15;
  const timeRatio = Math.max(0.05, Math.min(2.0, (timeMs / 1000.0) / dur));
  recordReviewForEvaluation(timeMs, grade);
  recordPersistentReviewRatio(timeRatio, grade);
  _reviewHistory.push({ timeMs: Math.max(100, timeMs), grade, durationSec: dur, timeRatio, ms: Date.now() });

  // Cooldown protections:
  // 1. Minimum 8 reviews warm-up before activating proactive interventions
  // 2. Dismissed fatigue has a 5-minute quiet period
  // 3. Post-break requires at least 8 fresh cards
  if (_reviewHistory.length < 8) return;
  if (Date.now() - _fatigueDismissedAt < 5 * 60 * 1000 || Date.now() - _lastBreakCompletedAt < 5 * 60 * 1000) return;

  const weights = await loadNeuralWeights();
  const sessionStats = getSessionStats();
  const elapsedSec = sessionStats ? (sessionStats.elapsedSec || 0) : 0;
  const features = extractTelemetryVector(card, timeMs, grade, _reviewHistory, elapsedSec, _reviewHistory.length, dur);

  let isFatigued = false, lapseRisk = 0.2, bestSec = 60, reason = '';

  if (weights) {
    const state = forwardCognitiveState(features, weights);
    if (state) {
      _currentCognitiveZ = state.z;
      lapseRisk = state.lapseRisk;
      const pauseEval = evaluateOptimalPause(state.z, weights);
      bestSec = pauseEval.bestSec;
      const drift = features[6]; // latency_drift vs historical baseline

      // Pure Tabula Rasa Policy anchored to Persistent Historical Baseline Ratio (% of allowed time):
      // 1. Fatigue is triggered if cognitive slowdown occurs (>25% above historical ratio) with elevated risk
      // 2. Or if projected lapse risk reaches critical failure levels (>= 50%)
      isFatigued = (drift > 0.25 && lapseRisk >= 0.28) || (lapseRisk >= 0.50);
      reason = drift > 0.20
        ? `Consumo tempo limite in salita (+${Math.round(drift * 100)}% vs percentuale consentita storica). Rischio lapse: ${Math.round(lapseRisk * 100)}%.`
        : `Carico cognitivo elevato rilevato dal modello neurale TPU (Rischio lapse: ${Math.round(lapseRisk * 100)}%).`;
    }
  }

  if (isFatigued) {
    _currentRecSec = bestSec;
    _currentRecData = { recommendedSec: bestSec, lapseRisk, reason };
    const snap = captureFatiguePromptSnapshot(card, timeMs, grade, _reviewHistory, features, lapseRisk, bestSec, reason);
    showFatigueModal(bestSec, reason, snap);
  }
}

export function showFatigueModal(seconds = 60, customMsg = '', snapshot = null) {
  const modal = get('ankiFatigueModal'), msgEl = get('ankiFatigueMsg'), btn = get('ankiFatigueActionBtn');
  if (!modal) return;
  if (msgEl && customMsg) msgEl.innerText = customMsg;
  if (btn) {
    const m = Math.floor(seconds / 60), s = seconds % 60;
    btn.innerText = s > 0 ? `Fai ${m}m ${s}s di Micro-Pausa` : `Fai ${m} min di Pausa`;
  }
  const dbg = get('ankiFatigueDebugContainer');
  if (dbg && snapshot) {
    dbg.innerHTML = buildDebugModalHtml(snapshot);
    dbg.classList.add('hidden');
  }
  modal.classList.remove('hidden');
}

export function hideFatigueModal(action = 'DISMISSED') {
  const modal = get('ankiFatigueModal');
  if (modal) modal.classList.add('hidden');
  _fatigueDismissedAt = Date.now();
  if (_currentRecData) {
    startFatigueEvaluation(action, _currentRecData, _reviewHistory);
    _currentRecData = null;
  }
}

export function startDynamicBreak() {
  const sec = _currentRecSec || 60;
  hideFatigueModal('BREAK_TAKEN');
  startMicroBreak(sec);
}

export function startMicroBreak(seconds = 60) {
  const breakModal = get('ankiBreakModal');
  if (!breakModal) return;
  const stats = getSessionStats();
  _sessionWasRunningBeforeBreak = !!(stats && stats.isRunning);
  if (_sessionWasRunningBeforeBreak) pauseSessionTimer();
  pauseCardTimer();

  const activeStage = get('ankiBreakActiveStage'), finishedStage = get('ankiBreakFinishedStage');
  if (activeStage) activeStage.classList.remove('hidden');
  if (finishedStage) finishedStage.classList.add('hidden');
  breakModal.classList.remove('hidden');

  _breakTotalSec = seconds; _breakRemainSec = seconds; updateBreakUI();
  if (_breakInterval) clearInterval(_breakInterval);
  _breakInterval = setInterval(() => {
    _breakRemainSec--; updateBreakUI();
    if (_breakRemainSec <= 0) onBreakCountdownCompleted();
  }, 1000);
}

function onBreakCountdownCompleted() {
  if (_breakInterval) { clearInterval(_breakInterval); _breakInterval = null; }
  playBreakFinishedSound();
  const activeStage = get('ankiBreakActiveStage'), finishedStage = get('ankiBreakFinishedStage');
  if (activeStage) activeStage.classList.add('hidden');
  if (finishedStage) finishedStage.classList.remove('hidden');
}

export async function stopMicroBreak() {
  if (_breakInterval) { clearInterval(_breakInterval); _breakInterval = null; }
  const breakModal = get('ankiBreakModal');
  if (breakModal) breakModal.classList.add('hidden');
  _lastBreakCompletedAt = Date.now();
  _reviewHistory = [];

  // Project continuous recovery of latent state z using TPU weights
  const weights = await loadNeuralWeights();
  if (_currentCognitiveZ && weights) {
    const recovered = projectRecovery(_currentCognitiveZ, _breakTotalSec, weights);
    if (recovered) {
      _currentCognitiveZ = recovered.zRecovered;
      _postBreakBaselineLapseRisk = recovered.lapseRisk;
    }
  }

  if (_sessionWasRunningBeforeBreak) { resumeSessionTimer(); _sessionWasRunningBeforeBreak = false; }
  const card = (typeof window !== 'undefined' && window.ankiGetCurrentCard) ? window.ankiGetCurrentCard() : null;
  if (card) startCardTimer(card);
}

function playBreakFinishedSound() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)(), now = ctx.currentTime;
    [659.25, 830.61, 987.77].forEach((freq, idx) => {
      const osc = ctx.createOscillator(), gain = ctx.createGain(), t = now + idx * 0.09;
      osc.type = 'sine'; osc.frequency.setValueAtTime(freq, t);
      gain.gain.setValueAtTime(0.001, t);
      gain.gain.exponentialRampToValueAtTime(0.12, t + 0.05);
      gain.gain.exponentialRampToValueAtTime(0.0001, t + 1.8);
      osc.connect(gain); gain.connect(ctx.destination);
      osc.start(t); osc.stop(t + 1.8);
    });
  } catch {}
  if ('vibrate' in navigator) try { navigator.vibrate([150, 100, 200]); } catch {}
}

function updateBreakUI() {
  const textEl = get('ankiBreakTimerText'), circleEl = get('ankiBreakCircle');
  if (textEl) textEl.innerText = `${Math.floor(_breakRemainSec / 60)}:${String(_breakRemainSec % 60).padStart(2, '0')}`;
  if (circleEl) {
    const cycle = _breakRemainSec % 12;
    circleEl.className = cycle >= 8
      ? 'w-28 h-28 rounded-full bg-[#42A5F5]/30 border-2 border-[#42A5F5] flex items-center justify-center transition-all duration-1000 transform scale-110 shadow-lg'
      : (cycle >= 4 ? 'w-28 h-28 rounded-full bg-[#66BB6A]/30 border-2 border-[#66BB6A] flex items-center justify-center transition-all duration-1000 transform scale-100 shadow-lg' : 'w-28 h-28 rounded-full bg-[#FFA726]/30 border-2 border-[#FFA726] flex items-center justify-center transition-all duration-1000 transform scale-90 shadow-lg');
  }
}

export function toggleFatigueDebug() {
  const dbg = get('ankiFatigueDebugContainer');
  if (dbg) dbg.classList.toggle('hidden');
}

if (typeof window !== 'undefined') {
  Object.assign(window, {
    ankiStartBreak: startMicroBreak, ankiStartDynamicBreak: startDynamicBreak,
    ankiDismissFatigue: () => hideFatigueModal('DISMISSED'), ankiStopBreak: stopMicroBreak,
    ankiToggleFatigueDebug: toggleFatigueDebug
  });
}
