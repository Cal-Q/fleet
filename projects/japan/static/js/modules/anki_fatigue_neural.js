// static/js/modules/anki_fatigue_neural.js — Neural Inference Engine for Cognitive Fatigue
// Runs TPU-trained Tabula Rasa weights in browser JS (<0.1ms). Strictly <= 200 lines invariant.

export { getPersistentBaselineRatios, recordPersistentReviewRatio, extractTelemetryVector } from './anki_fatigue_telemetry.js';

let _weights = null, _weightsPromise = null;

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
    pill.title = 'Modello neurale non caricato — fallback euristico attivo';
  }
}

export async function loadNeuralWeights() {
  if (_weights) return _weights;
  if (_weightsPromise) return _weightsPromise;
  _weightsPromise = (async () => {
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
  })();
  return _weightsPromise;
}

function silu(x) {
  return x / (1.0 + Math.exp(-Math.max(-20, Math.min(20, x))));
}

function dense(input, kernel, bias, applySilu = false) {
  const inDim = input.length, outDim = bias.length;
  const out = new Float32Array(outDim);
  for (let j = 0; j < outDim; j++) {
    let sum = bias[j];
    for (let i = 0; i < inDim; i++) sum += input[i] * kernel[i][j];
    out[j] = applySilu ? silu(sum) : sum;
  }
  return out;
}

export function forwardCognitiveState(features, weights) {
  if (!weights || !weights.encoder || !weights.dynamics) return null;
  const enc = weights.encoder, dyn = weights.dynamics;

  const h0 = dense(features, enc.Dense_0.kernel, enc.Dense_0.bias, true);
  const h1 = dense(h0, enc.Dense_1.kernel, enc.Dense_1.bias, true);
  for (let i = 0; i < h1.length; i++) h1[i] += h0[i];
  const z = dense(h1, enc.Dense_2.kernel, enc.Dense_2.bias, false);

  const hRate = dense(z, dyn.Dense_3.kernel, dyn.Dense_3.bias, true);
  const ratingLogits = dense(hRate, dyn.Dense_4.kernel, dyn.Dense_4.bias, false);
  const maxL = Math.max(...ratingLogits);
  const expL = ratingLogits.map(v => Math.exp(v - maxL));
  const sumExp = expL.reduce((a, b) => a + b, 0);
  const ratingProbs = expL.map(v => v / sumExp);

  const hLat = dense(z, dyn.Dense_0.kernel, dyn.Dense_0.bias, true);
  const latMu = dense(hLat, dyn.Dense_1.kernel, dyn.Dense_1.bias, false)[0];

  return { z, lapseRisk: ratingProbs[0], goodEasyProb: (ratingProbs[2] || 0) + (ratingProbs[3] || 0), ratingProbs, latMu };
}

export function projectRecoveryLat(z, deltaTSec, weights) {
  if (!weights || !weights.recovery || !weights.dynamics) return 0;
  const rec = weights.recovery, dyn = weights.dynamics;
  const logDt = Math.log(1.0 + Math.max(0, deltaTSec));
  const inp = new Float32Array(z.length + 1);
  inp.set(z, 0); inp[z.length] = logDt;

  const hRec = dense(inp, rec.Dense_0.kernel, rec.Dense_0.bias, true);
  const deltaZ = dense(hRec, rec.Dense_1.kernel, rec.Dense_1.bias, false);
  const zRec = new Float32Array(z.length);
  for (let i = 0; i < z.length; i++) zRec[i] = z[i] + deltaZ[i];

  const hLat = dense(zRec, dyn.Dense_0.kernel, dyn.Dense_0.bias, true);
  return dense(hLat, dyn.Dense_1.kernel, dyn.Dense_1.bias, false)[0];
}

export function projectRecovery(z, deltaTSec, weights) {
  if (!weights || !weights.recovery || !weights.dynamics) return null;
  const rec = weights.recovery, dyn = weights.dynamics;
  const logDt = Math.log(1.0 + Math.max(0, deltaTSec));
  const inp = new Float32Array(z.length + 1);
  inp.set(z, 0); inp[z.length] = logDt;

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

  const hLat = dense(zRecovered, dyn.Dense_0.kernel, dyn.Dense_0.bias, true);
  const latMu = dense(hLat, dyn.Dense_1.kernel, dyn.Dense_1.bias, false)[0];

  return { zRecovered, lapseRisk: probs[0], goodEasyProb: (probs[2] || 0) + (probs[3] || 0), latMu };
}

export function evaluateOptimalPause(z, weights, drift = 0.0, lapseRisk = 0.25) {
  const lat0 = projectRecoveryLat(z, 0, weights);
  const latInf = projectRecoveryLat(z, 1800, weights);
  const totalRecoverable = lat0 - latInf;

  if (totalRecoverable <= 1e-6) {
    return { bestSec: 60, bestMin: 1, severity: 0.0, targetRecFrac: 0.50 };
  }

  // Model-driven fatigue severity score S in [0, 1] derived directly from user performance & model state
  const riskFactor = Math.max(0.0, (lapseRisk - 0.20) / 0.30);
  const driftFactor = Math.max(0.0, drift / 0.50);
  const severity = Math.min(1.0, Math.max(0.0, riskFactor * 0.5 + driftFactor * 0.5));

  // Continuous target recovery fraction (45% for mild reset up to 85% for deep recharge)
  const targetRecFrac = 0.45 + 0.40 * severity;
  const targetReduction = targetRecFrac * totalRecoverable;

  // Continuous binary search solver over TPU recovery operator
  let low = 1.0, high = 1800.0;
  for (let it = 0; it < 25; it++) {
    const mid = (low + high) / 2.0;
    const curLat = projectRecoveryLat(z, mid, weights);
    if ((lat0 - curLat) < targetReduction) low = mid; else high = mid;
  }

  const bestSec = Math.max(30, Math.min(600, Math.round((low + high) / 2.0)));
  return {
    bestSec,
    bestMin: Math.round(bestSec / 60),
    severity: Math.round(severity * 1000) / 1000,
    targetRecFrac: Math.round(targetRecFrac * 1000) / 1000,
    recoveredLat: lat0 - targetReduction,
    totalRecoverable
  };
}
