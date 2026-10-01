// static/js/modules/anki_logger.js — Persistent Telemetry & Exhaustive Event Logger
// Strictly <= 200 lines invariant.

const RING_BUFFER_KEY = 'anki_debug_ring_buffer';
const MAX_RING_BUFFER = 200;
const PERSIST_LIMIT = 50;
let _memoryBuffer = [];

function loadRingBuffer() {
  try {
    const raw = localStorage.getItem(RING_BUFFER_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function flushRingBufferToStorage() {
  try {
    const slice = _memoryBuffer.length > PERSIST_LIMIT
      ? _memoryBuffer.slice(_memoryBuffer.length - PERSIST_LIMIT)
      : _memoryBuffer;
    localStorage.setItem(RING_BUFFER_KEY, JSON.stringify(slice));
  } catch {}
}

let _saveTimeout = null;
function scheduleRingBufferSave(forceImmediate = false) {
  if (forceImmediate) {
    if (_saveTimeout) clearTimeout(_saveTimeout);
    _saveTimeout = null;
    flushRingBufferToStorage();
    return;
  }
  if (_saveTimeout) return;
  _saveTimeout = setTimeout(() => {
    _saveTimeout = null;
    flushRingBufferToStorage();
  }, 5000);
}

_memoryBuffer = loadRingBuffer();

export function ankiLog(level, category, action, details = {}) {
  const isErr = (level === 'ERROR');
  const entry = {
    id: Date.now() + Math.random().toString(36).substring(2, 6),
    time: new Date().toISOString(),
    ms: Date.now(),
    level: level.toUpperCase(),
    cat: category.toUpperCase(),
    act: action,
    det: details,
    online: typeof navigator !== 'undefined' ? navigator.onLine : true
  };

  _memoryBuffer.push(entry);
  if (_memoryBuffer.length > MAX_RING_BUFFER) _memoryBuffer.shift();
  scheduleRingBufferSave(isErr);

  const styleMap = {
    ERROR: 'color: #EF5350; font-weight: bold;',
    WARN: 'color: #FFA726; font-weight: bold;',
    ACTION: 'color: #42A5F5; font-weight: bold;',
    DATA: 'color: #66BB6A;',
    INFO: 'color: #AB47BC;'
  };
  const style = styleMap[entry.level] || 'color: #888;';
  console.log(`%c[AnkiLog:${entry.cat}] ${entry.act}`, style, entry.det);

  try {
    if (typeof window !== 'undefined' && window.ankiOnLogUpdate) {
      window.ankiOnLogUpdate(entry);
    }
  } catch {}
  return entry;
}

export function getLogs(filterCat = null, search = '') {
  let logs = [..._memoryBuffer];
  if (filterCat && filterCat !== 'ALL') {
    logs = logs.filter(l => l.cat === filterCat || l.level === filterCat);
  }
  if (search && search.trim()) {
    const s = search.toLowerCase();
    logs = logs.filter(l => 
      l.act.toLowerCase().includes(s) || 
      JSON.stringify(l.det).toLowerCase().includes(s)
    );
  }
  return logs;
}

export function clearLogs() {
  _memoryBuffer = [];
  try { localStorage.removeItem(RING_BUFFER_KEY); } catch {}
  ankiLog('INFO', 'SYSTEM', 'LOGS_CLEARED', { reason: 'user_action' });
}

export function exportLogsAsJson() {
  return JSON.stringify(_memoryBuffer, null, 2);
}

export async function sendLogsToServer() {
  ankiLog('INFO', 'NET', 'SENDING_LOGS_TO_SERVER', { count: _memoryBuffer.length });
  try {
    const res = await fetch('/api/anki/client_logs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        device: typeof navigator !== 'undefined' ? navigator.userAgent : 'unknown',
        timestamp: new Date().toISOString(),
        logs: _memoryBuffer
      })
    });
    const data = await res.json();
    ankiLog('INFO', 'NET', 'LOGS_SENT_SUCCESS', {
      server_status: data.status,
      received: data.received
    });
    return { ok: true, data };
  } catch (err) {
    ankiLog('ERROR', 'NET', 'LOGS_SENT_FAILED', { error: String(err) });
    return { ok: false, error: String(err) };
  }
}

if (typeof window !== 'undefined') {
  window.addEventListener('error', (e) => {
    ankiLog('ERROR', 'SYSTEM', 'UNCAUGHT_ERROR', {
      message: e.message,
      filename: e.filename,
      lineno: e.lineno,
      colno: e.colno,
      stack: e.error ? e.error.stack : null
    });
  });

  window.addEventListener('unhandledrejection', (e) => {
    ankiLog('ERROR', 'SYSTEM', 'UNHANDLED_REJECTION', {
      reason: String(e.reason),
      stack: e.reason && e.reason.stack ? e.reason.stack : null
    });
  });

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') flushRingBufferToStorage();
  });

  window.ankiLog = ankiLog;
  window.ankiGetLogs = getLogs;
  window.ankiClearLogs = clearLogs;
  window.ankiExportLogs = exportLogsAsJson;
  window.ankiSendLogs = sendLogsToServer;
}
