// static/js/modules/anki_fatigue_snapshot.js — Exhaustive Fatigue Diagnostic Snapshot Engine
// Captures full session history & neural telemetry for prompted micro-pauses. Strictly <= 200 lines.

import { ankiLog } from './anki_logger.js';

const STORAGE_LATEST_KEY = 'anki_latest_fatigue_snapshot';
const STORAGE_HISTORY_KEY = 'anki_fatigue_snapshots_history';
const MAX_SNAPSHOT_HISTORY = 20;

export function captureFatiguePromptSnapshot(card, timeMs, grade, history, features, lapseRisk, bestSec, reason) {
  const drift = features && features.length > 6 ? features[6] : 0.0;
  const meanLat10Ms = features && features.length > 1 ? Math.round(Math.exp(features[1])) : timeMs;
  const meanLat30Ms = features && features.length > 4 ? Math.round(Math.exp(features[4])) : timeMs;

  const sessionCards = (history || []).map((h, idx) => ({
    seq: idx + 1,
    cid: h.cid || (h.card ? h.card.id : null),
    front: (h.front || (h.card ? h.card.front : '') || '').substring(0, 50),
    deck: (h.deck || (h.card ? h.card.deck_name : '') || ''),
    grade: h.grade,
    time_ms: h.timeMs,
    duration_sec: h.durationSec || 15,
    time_ratio: Math.round((h.timeRatio || 0) * 1000) / 1000,
    time_str: new Date(h.ms || Date.now()).toLocaleTimeString()
  }));

  const snapshot = {
    id: `fp_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
    timestamp: new Date().toISOString(),
    trigger_cid: card ? card.id : null,
    trigger_front: card ? (card.front || '').substring(0, 50) : '',
    trigger_grade: grade,
    trigger_latency_ms: timeMs,
    drift: Math.round(drift * 1000) / 1000,
    lapse_risk: Math.round(lapseRisk * 1000) / 1000,
    mean_lat_10_ms: meanLat10Ms,
    mean_lat_30_ms: meanLat30Ms,
    recommended_sec: bestSec,
    reason: reason || '',
    session_cards_count: sessionCards.length,
    session_cards: sessionCards,
    neural_features: features ? Array.from(features) : [],
    device: typeof navigator !== 'undefined' ? navigator.userAgent : 'unknown'
  };

  persistSnapshotLocally(snapshot);
  sendSnapshotToServer(snapshot);

  ankiLog('WARN', 'FATIGUE', 'PAUSE_PROMPTED_SNAPSHOT', {
    trigger: snapshot.trigger_front,
    drift: snapshot.drift,
    lapseRisk: snapshot.lapse_risk,
    sessionCards: snapshot.session_cards_count
  });

  return snapshot;
}

function persistSnapshotLocally(snapshot) {
  try {
    if (typeof localStorage === 'undefined') return;
    localStorage.setItem(STORAGE_LATEST_KEY, JSON.stringify(snapshot));
    const histRaw = localStorage.getItem(STORAGE_HISTORY_KEY);
    const hist = histRaw ? JSON.parse(histRaw) : [];
    hist.push(snapshot);
    if (hist.length > MAX_SNAPSHOT_HISTORY) hist.splice(0, hist.length - MAX_SNAPSHOT_HISTORY);
    localStorage.setItem(STORAGE_HISTORY_KEY, JSON.stringify(hist));
  } catch (e) {
    console.warn('[FatigueSnapshot] Local storage error:', e);
  }
}

async function sendSnapshotToServer(snapshot) {
  try {
    if (typeof fetch === 'undefined') return;
    await fetch('/api/anki/fatigue_event', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(snapshot)
    });
  } catch (e) {
    console.warn('[FatigueSnapshot] Server ingestion error:', e);
  }
}

export function getLatestStoredSnapshot() {
  try {
    if (typeof localStorage === 'undefined') return null;
    const raw = localStorage.getItem(STORAGE_LATEST_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function buildDebugModalHtml(snapshot) {
  if (!snapshot || !snapshot.session_cards) return '<p class="text-xs text-gray-400">Nessun dato di sessione disponibile.</p>';
  const cards = snapshot.session_cards;
  const rows = cards.map(c => {
    const isTrigger = (c.cid === snapshot.trigger_cid && c.time_ms === snapshot.trigger_latency_ms);
    const gradeLabel = c.grade === 1 ? '<span class="text-red-400 font-bold">Again</span>' : (c.grade === 3 ? '<span class="text-green-400">Good</span>' : `G${c.grade}`);
    const rowClass = isTrigger ? 'bg-red-950/40 text-red-200 font-semibold' : 'hover:bg-neutral-800/50';
    return `<tr class="border-b border-neutral-800/40 ${rowClass}">
      <td class="p-1 text-center">${c.seq}</td>
      <td class="p-1">${c.time_str}</td>
      <td class="p-1 truncate max-w-[120px]" title="${c.front}">${c.front}</td>
      <td class="p-1 text-center">${gradeLabel}</td>
      <td class="p-1 text-right">${(c.time_ms/1000).toFixed(2)}s</td>
      <td class="p-1 text-right text-gray-400">${Math.round(c.time_ratio*100)}%</td>
    </tr>`;
  }).join('');

  return `
    <div class="text-left font-sans text-xs space-y-2">
      <div class="grid grid-cols-2 gap-1 text-[11px] bg-neutral-900/80 p-2 rounded border border-neutral-800">
        <div><span class="text-gray-400">Carte Sessione:</span> <b class="text-white">${snapshot.session_cards_count}</b></div>
        <div><span class="text-gray-400">Pausa Neurale:</span> <b class="text-emerald-400">${Math.floor(snapshot.recommended_sec/60)}m ${snapshot.recommended_sec%60}s (${snapshot.recommended_sec}s)</b></div>
        <div><span class="text-gray-400">Drift Latenza:</span> <b class="${snapshot.drift > 0.25 ? 'text-amber-400' : 'text-white'}">+${Math.round(snapshot.drift*100)}%</b></div>
        <div><span class="text-gray-400">Rischio Lapse:</span> <b class="${snapshot.lapse_risk >= 0.28 ? 'text-red-400' : 'text-white'}">${Math.round(snapshot.lapse_risk*100)}%</b></div>
        <div><span class="text-gray-400">Latenza 10 vs 30:</span> <b class="text-white">${(snapshot.mean_lat_10_ms/1000).toFixed(1)}s / ${(snapshot.mean_lat_30_ms/1000).toFixed(1)}s</b></div>
        <div><span class="text-gray-400">Trigger:</span> <b class="text-amber-300 truncate inline-block max-w-[85px] align-bottom" title="${snapshot.trigger_front}">${snapshot.trigger_front}</b></div>
      </div>
      <div class="max-h-48 overflow-y-auto rounded border border-neutral-800 overscroll-contain">
        <table class="w-full text-[11px]">
          <thead class="bg-neutral-900 text-gray-400 sticky top-0 border-b border-neutral-800">
            <tr>
              <th class="p-1 text-center">#</th>
              <th class="p-1 text-left">Ora</th>
              <th class="p-1 text-left">Carta</th>
              <th class="p-1 text-center">Esito</th>
              <th class="p-1 text-right">Tempo</th>
              <th class="p-1 text-right">%Max</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>
  `;
}
