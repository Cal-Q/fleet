// static/js/modules/anki_fatigue_neural.js — Neural Inference Engine for Cognitive Fatigue
// Runs TPU-trained Tabula Rasa weights in browser JS (<0.1ms). Strictly <= 200 lines invariant.

let _weights = null;

function updateNeuralStatusPill(state) {
  const icon = document.getElementById('ankiNeuralStatusIcon');
  const text = document.getElementById('ankiNeuralStatusText');
  const pill = document.getElementById('ankiNeuralStatusPill');
  if (!icon || !text || !pill) return;
  if (state === 'ok') {
    icon.textContent = '🧠'; text.textContent = 'AI'; text.className = 'text-[#66BB6A] text-[10px] font-bold';
    pill.className = pill.className.replace('border-[#2C2C2C]', 'border-[#66BB6A]/60').replace('border-[#EF5350]/60','border-[#66BB6A]/60');
    pill.title = 'Modello neurale TPU attivo';
  } else if (state === 'err') {
    icon.textContent = '⚠️'; text.textContent = 'AI'; text.className = 'text-[#FFA726] text-[10px]';
    pill.title = 'Modello neurale non caricato — sistema euristico attivo';
  }
}

export async function loadNeuralWeights() {
  if (_weights) return _weights;
  try {
    const res = await fetch('/static/data/tpu_model_output/tabula_rasa_tpu_weights.json');
    if (res.ok) {
      _weights = await res.json();
      updateNeuralStatusPill('ok');
      return _weights;
    }
  } catch (e) {
    console.warn('[NeuralFatigue] Could not load weights:', e);
  }
  updateNeuralStatusPill('err');
  return null;
}

function silu(x) {
  return x / (1.0 + Math.exp(-Math.max(-20, Math.min(20, x))));
}

function dense(input, kernel, bias, applySilu = false) {
  const inDim = input.length;
  const outDim = bias.length;
  const out = new Float32Array(outDim);
  for (let j = 0; j < outDim; j++) {
    let sum = bias[j];
    for (let i = 0; i < inDim; i++) {
      sum += input[i] * kernel[i][j];
    }
    out[j] = applySilu ? silu(sum) : sum;
  }
  return out;
}

export function forwardCognitiveState(features, weights) {
  if (!weights || !weights.encoder) return null;
  const enc = weights.encoder;
  const dyn = weights.dynamics;

  // Encoder Dense 0
  const h0 = dense(features, enc.Dense_0.kernel, enc.Dense_0.bias, true);
  // Encoder Dense 1 + residual
  const h1 = dense(h0, enc.Dense_1.kernel, enc.Dense_1.bias, true);
  for (let i = 0; i < h1.length; i++) h1[i] += h0[i];
  // Latent cognitive state z_t (64 dimensions)
  const z = dense(h1, enc.Dense_2.kernel, enc.Dense_2.bias, false);

  // Dynamics: Latency & Rating logits
  const hRate = dense(z, dyn.Dense_3.kernel, dyn.Dense_3.bias, true);
  const ratingLogits = dense(hRate, dyn.Dense_4.kernel, dyn.Dense_4.bias, false);

  // Softmax on rating logits: [Again, Hard, Good, Easy]
  const maxL = Math.max(...ratingLogits);
  const expL = ratingLogits.map(v => Math.exp(v - maxL));
  const sumExp = expL.reduce((a, b) => a + b, 0);
  const ratingProbs = expL.map(v => v / sumExp);

  const lapseRisk = ratingProbs[0]; // P(Again)
  const goodEasyProb = (ratingProbs[2] || 0) + (ratingProbs[3] || 0);

  return { z, lapseRisk, goodEasyProb, ratingProbs };
}

export function projectRecovery(z, deltaTSec, weights) {
  if (!weights || !weights.recovery || !weights.dynamics) return null;
  const rec = weights.recovery;
  const dyn = weights.dynamics;

  const logDt = Math.log(1.0 + Math.max(0, deltaTSec));
  const inp = new Float32Array(z.length + 1);
  inp.set(z, 0);
  inp[z.length] = logDt;

  const hRec = dense(inp, rec.Dense_0.kernel, rec.Dense_0.bias, true);
  const deltaZ = dense(hRec, rec.Dense_1.kernel, rec.Dense_1.bias, false);

  const zRecovered = new Float32Array(z.length);
  for (let i = 0; i < z.length; i++) zRecovered[i] = z[i] + deltaZ[i];

  const hRate = dense(zRecovered, dyn.Dense_3.kernel, dyn.Dense_3.bias, true);
  const logits = dense(hRate, dyn.Dense_4.kernel, dyn.Dense_4.bias, false);
  const maxL = Math.max(...logits);
  const expL = logits.map(v => Math.exp(v - maxL));
  const sumExp = expL.reduce((a, b) => a + b, 0);
  const probs = expL.map(v => v / sumExp);

  return { zRecovered, lapseRisk: probs[0], goodEasyProb: (probs[2] || 0) + (probs[3] || 0) };
}

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

export function evaluateOptimalPause(z, weights) {
  const candidatesSec = [60, 120, 180, 300, 480];
  const baseline = projectRecovery(z, 0, weights);
  const baseProb = baseline ? baseline.goodEasyProb : 0.65;
  let bestSec = 60, maxRate = -999;
  const results = [];
  for (const sec of candidatesSec) {
    const proj = projectRecovery(z, sec, weights);
    const prob = proj ? proj.goodEasyProb : baseProb, gain = prob - baseProb, rate = gain / (sec / 60.0);
    results.push({ sec, prob, gain, rate });
    if (rate > maxRate) { maxRate = rate; bestSec = sec; }
  }
  const res300 = results.find(r => r.sec === 300), res60 = results.find(r => r.sec === 60);
  if (res300 && res60 && (res300.gain - res60.gain) > 0.05) bestSec = 300;
  return { bestSec, bestMin: Math.round(bestSec / 60), maxRate, baseProb, results };
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
