// static/js/modules/anki_fatigue_eval.js — Empirical Fatigue Evaluation & Counterfactual Logger
// Tracks pre vs post-break accuracy & latency to verify model performance. Strictly <= 200 lines.

import { ankiLog } from './anki_logger.js';

const EVAL_STORAGE_KEY = 'anki_fatigue_eval_v1';
let _pendingEvaluation = null; // { id, type, preStats, postReviews: [] }

export function getEvaluationHistory() {
  try {
    const raw = localStorage.getItem(EVAL_STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveEvaluationEvent(record) {
  try {
    const history = getEvaluationHistory();
    history.push(record);
    if (history.length > 200) history.shift();
    localStorage.setItem(EVAL_STORAGE_KEY, JSON.stringify(history));
  } catch {}
}

export function startFatigueEvaluation(decision, modelOutput, recentHistory) {
  const preReviews = recentHistory.slice(-10);
  const preAccuracy = preReviews.length
    ? preReviews.filter(r => r.grade >= 3).length / preReviews.length
    : 0.5;
  const preMeanLat = preReviews.length
    ? preReviews.reduce((a, b) => a + b.timeMs, 0) / preReviews.length
    : 4000;

  _pendingEvaluation = {
    id: 'eval_' + Date.now(),
    timestamp: new Date().toISOString(),
    epochMs: Date.now(),
    action: decision, // 'BREAK_TAKEN' | 'DISMISSED'
    recommendedBreakSec: modelOutput.recommendedSec || 60,
    actualBreakSec: modelOutput.actualBreakSec || 0,
    predictedLapseRisk: modelOutput.lapseRisk || 0,
    predictedRecoveryGain: modelOutput.predictedGain || 0,
    preAccuracy: Math.round(preAccuracy * 1000) / 10,
    preMeanLatencyMs: Math.round(preMeanLat),
    postReviews: []
  };

  ankiLog('ACTION', 'FATIGUE_EVAL_START', {
    action: decision,
    recommendedSec: _pendingEvaluation.recommendedBreakSec,
    preAccuracy: _pendingEvaluation.preAccuracy
  });
}

export function recordReviewForEvaluation(timeMs, grade) {
  if (!_pendingEvaluation) return;

  _pendingEvaluation.postReviews.push({ timeMs, grade });

  // Complete evaluation after 10 subsequent cards
  if (_pendingEvaluation.postReviews.length >= 10) {
    const post = _pendingEvaluation.postReviews;
    const postAccuracy = post.filter(r => r.grade >= 3).length / post.length;
    const postMeanLat = post.reduce((a, b) => a + b.timeMs, 0) / post.length;

    const completed = {
      ..._pendingEvaluation,
      postAccuracy: Math.round(postAccuracy * 1000) / 10,
      postMeanLatencyMs: Math.round(postMeanLat),
      accuracyDelta: Math.round((postAccuracy * 100 - _pendingEvaluation.preAccuracy) * 10) / 10,
      latencyDeltaMs: Math.round(postMeanLat - _pendingEvaluation.preMeanLatencyMs),
      recoveryVerified: (postAccuracy * 100 > _pendingEvaluation.preAccuracy)
    };

    delete completed.postReviews;
    saveEvaluationEvent(completed);

    ankiLog('DATA', 'FATIGUE_EVAL_COMPLETE', {
      action: completed.action,
      accDelta: `${completed.accuracyDelta >= 0 ? '+' : ''}${completed.accuracyDelta}%`,
      latDeltaMs: completed.latencyDeltaMs,
      verified: completed.recoveryVerified
    });

    _pendingEvaluation = null;
  }
}

export function getEvaluationSummary() {
  const events = getEvaluationHistory();
  const taken = events.filter(e => e.action === 'BREAK_TAKEN');
  const dismissed = events.filter(e => e.action === 'DISMISSED');

  const avgAccDeltaTaken = taken.length
    ? taken.reduce((a, b) => a + (b.accuracyDelta || 0), 0) / taken.length
    : 0;
  const avgAccDeltaDismissed = dismissed.length
    ? dismissed.reduce((a, b) => a + (b.accuracyDelta || 0), 0) / dismissed.length
    : 0;

  return {
    totalEvents: events.length,
    breaksTakenCount: taken.length,
    breaksDismissedCount: dismissed.length,
    avgAccuracyGainAfterBreak: Math.round(avgAccDeltaTaken * 10) / 10,
    avgAccuracyGainWhenDismissed: Math.round(avgAccDeltaDismissed * 10) / 10,
    events
  };
}
