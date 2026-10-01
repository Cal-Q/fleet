// static/js/modules/anki_fatigue_telemetry.js — Telemetry Extraction & Baseline Pool
// Maintains persistent cognitive baseline ratios and builds feature vectors for TPU inference. Strictly <= 200 lines.

const BASELINE_KEY = 'anki_neural_persistent_timeratios';
const DEFAULT_BASELINE_RATIO = 0.22;

export function getPersistentBaselineRatios() {
  try {
    const raw = typeof localStorage !== 'undefined' ? localStorage.getItem(BASELINE_KEY) : null;
    if (raw) {
      const arr = JSON.parse(raw);
      if (Array.isArray(arr) && arr.length >= 10) return arr.slice(-60);
    }
  } catch {}
  return Array(30).fill({ timeRatio: DEFAULT_BASELINE_RATIO, grade: 3 });
}

export function recordPersistentReviewRatio(timeRatio, grade) {
  try {
    if (typeof localStorage === 'undefined') return;
    const arr = getPersistentBaselineRatios();
    const clamped = Math.max(0.05, Math.min(2.0, timeRatio || DEFAULT_BASELINE_RATIO));
    arr.push({ timeRatio: clamped, grade: grade === 1 ? 1 : 3 });
    if (arr.length > 80) arr.splice(0, arr.length - 80);
    localStorage.setItem(BASELINE_KEY, JSON.stringify(arr));
  } catch {}
}

export function extractTelemetryVector(card, timeMs, grade, history, sessionElapsedSec, sessionCardIdx, cardDurationSec = 15) {
  const dur = (cardDurationSec && cardDurationSec > 0) ? cardDurationSec : 15;
  const currentRatio = Math.max(0.05, Math.min(2.0, (timeMs / 1000.0) / dur));
  const logLat = Math.log(Math.max(100, currentRatio * 15000));
  const isLapse = (grade === 1) ? 1.0 : 0.0;

  const last10 = history.slice(-10);
  const ratio10 = last10.map(h => h.timeRatio || Math.max(0.05, Math.min(2.0, (h.timeMs / 1000.0) / (h.durationSec || 15))));
  const lat10 = ratio10.map(r => Math.log(r * 15000));
  const meanLat10 = lat10.length ? lat10.reduce((a, b) => a + b, 0) / lat10.length : logLat;
  const stdLat10 = lat10.length > 1 ? Math.sqrt(lat10.reduce((a, b) => a + Math.pow(b - meanLat10, 2), 0) / lat10.length) : 0.0;
  const lapses10 = last10.length ? last10.filter(h => h.grade === 1).length / last10.length : isLapse;

  // Persistent historical baseline pool: anchors baseline in % of maximum allowed time
  const persistent = getPersistentBaselineRatios();
  const baselinePool = history.length >= 30 ? history.slice(-30) : [...persistent.slice(-(30 - history.length)), ...history];
  const ratio30 = baselinePool.map(h => h.timeRatio || Math.max(0.05, Math.min(2.0, (h.timeMs / 1000.0) / (h.durationSec || 15))));
  const lat30 = ratio30.map(r => Math.log(r * 15000));
  const meanLat30 = lat30.reduce((a, b) => a + b, 0) / lat30.length;
  const lapses30 = baselinePool.filter(h => h.grade === 1).length / baselinePool.length;

  const latencyDrift = meanLat10 - meanLat30;
  const now = new Date();
  const hour = now.getHours() + now.getMinutes() / 60.0;
  const circSin = Math.sin(2.0 * Math.PI * hour / 24.0);
  const circCos = Math.cos(2.0 * Math.PI * hour / 24.0);

  const ivl = card ? (card.ivl || 0) : 0;
  const lastIvl = card ? (card.last_ivl || card.ivl || 0) : 0;
  const factor = card ? (card.factor || 2500) : 2500;
  const revType = card ? (card.type || card.queue || 1) : 1;
  const lastTime = history.length ? history[history.length - 1].ms : Date.now();
  const interGapSec = Math.max(0, (Date.now() - lastTime) / 1000.0);

  return new Float32Array([
    logLat, meanLat10, stdLat10, lapses10, meanLat30, lapses30, latencyDrift,
    sessionCardIdx, sessionElapsedSec, interGapSec, circSin, circCos,
    ivl, lastIvl, factor, revType
  ]);
}
