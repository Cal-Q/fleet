// static/js/modules/anki_web_persistence.js — Local-First Settings & Timers Persistence
// Strictly <= 200 lines invariant.

import { ankiLog } from './anki_logger.js';
import { saveLocalSettings, getLocalSettings } from './anki_web_db.js';

let _syncTimeout = null, _pendingUpdates = {};

const KEY_MAP = {
  anki_deck_timers: 'deck_timers',
  anki_timer_duration: 'timer_duration',
  anki_session_target_min: 'session_target_min',
  anki_furigana_mode: 'furigana_mode',
  anki_front_font_size: 'front_font_size',
  anki_back_font_size: 'back_font_size',
  anki_collapsed_decks: 'collapsed_decks'
};

const DEFAULT_SETTINGS = {
  deck_timers: {},
  timer_duration: 15,
  session_target_min: 25,
  furigana_mode: 'unstudied',
  front_font_size: 38,
  back_font_size: 20,
  collapsed_decks: []
};

export function getExplicitLocalSettings() {
  const explicit = {};
  const t = localStorage.getItem('anki_deck_timers');
  if (t !== null) { try { explicit.deck_timers = JSON.parse(t); } catch {} }
  const d = localStorage.getItem('anki_timer_duration');
  if (d !== null) explicit.timer_duration = parseInt(d, 10);
  const s = localStorage.getItem('anki_session_target_min');
  if (s !== null) explicit.session_target_min = parseInt(s, 10);
  const f = localStorage.getItem('anki_furigana_mode');
  if (f !== null) explicit.furigana_mode = f;
  const ff = localStorage.getItem('anki_front_font_size');
  if (ff !== null) explicit.front_font_size = parseInt(ff, 10);
  const bf = localStorage.getItem('anki_back_font_size');
  if (bf !== null) explicit.back_font_size = parseInt(bf, 10);
  const c = localStorage.getItem('anki_collapsed_decks');
  if (c !== null) { try { explicit.collapsed_decks = JSON.parse(c); } catch {} }
  return explicit;
}

export function getLocalSettingsSnapshot() {
  const e = getExplicitLocalSettings();
  return {
    deck_timers: e.deck_timers || {},
    timer_duration: e.timer_duration !== undefined ? e.timer_duration : DEFAULT_SETTINGS.timer_duration,
    session_target_min: e.session_target_min !== undefined ? e.session_target_min : DEFAULT_SETTINGS.session_target_min,
    furigana_mode: e.furigana_mode || DEFAULT_SETTINGS.furigana_mode,
    front_font_size: e.front_font_size || DEFAULT_SETTINGS.front_font_size,
    back_font_size: e.back_font_size || DEFAULT_SETTINGS.back_font_size,
    collapsed_decks: e.collapsed_decks || []
  };
}

function readAndroidBridgeSettings() {
  try {
    if (window.AndroidSettingsBridge?.getPersistedSettings) {
      const raw = window.AndroidSettingsBridge.getPersistedSettings();
      if (raw && typeof raw === 'string' && raw.trim().startsWith('{')) return JSON.parse(raw);
    }
  } catch (err) {
    ankiLog('WARN', 'BRIDGE', 'ANDROID_BRIDGE_READ_ERROR', { err: String(err) });
  }
  return null;
}

function saveAndroidBridgeSettings(settings) {
  try {
    if (window.AndroidSettingsBridge?.savePersistedSettings) {
      window.AndroidSettingsBridge.savePersistedSettings(JSON.stringify(settings));
    }
  } catch {}
}

export async function initSettingsSync(onUpdateCallback = null) {
  let combined = { ...DEFAULT_SETTINGS };

  // 0. Initial Server Embedding (from page load)
  const initS = (typeof window !== 'undefined' && window.__INITIAL_SETTINGS__) ? window.__INITIAL_SETTINGS__ : null;
  if (initS && typeof initS === 'object') {
    combined = { ...combined, ...initS, deck_timers: { ...(combined.deck_timers || {}), ...(initS.deck_timers || {}) } };
  }

  // 1. Android Bridge (External SD Card)
  const bridgeSettings = readAndroidBridgeSettings();
  if (bridgeSettings && typeof bridgeSettings === 'object') {
    combined = { ...combined, ...bridgeSettings, deck_timers: { ...(combined.deck_timers || {}), ...(bridgeSettings.deck_timers || {}) } };
    ankiLog('DATA', 'SETTINGS', 'RESTORED_FROM_ANDROID_BRIDGE', bridgeSettings);
  }

  // 2. IndexedDB Local Cache
  try {
    const cached = await getLocalSettings();
    if (cached && typeof cached === 'object') {
      combined = { ...combined, ...cached, deck_timers: { ...(combined.deck_timers || {}), ...(cached.deck_timers || {}) } };
      ankiLog('DATA', 'SETTINGS', 'RESTORED_FROM_INDEXEDDB', cached);
    }
  } catch {}

  // 3. Explicit LocalStorage Overrides
  const explicit = getExplicitLocalSettings();
  const explicitTimers = (explicit.deck_timers && Object.keys(explicit.deck_timers).length > 0) ? explicit.deck_timers : {};
  combined = { ...combined, ...explicit, deck_timers: { ...(combined.deck_timers || {}), ...explicitTimers } };

  applyServerSettings(combined);
  saveLocalSettings(combined);
  saveAndroidBridgeSettings(combined);
  if (typeof onUpdateCallback === 'function') onUpdateCallback(combined);

  // 4. Background cloud sync with backend
  try {
    const res = await fetch('/api/anki/settings');
    const data = await res.json();
    if (data.status === 'ok' && data.settings) {
      combined = {
        ...combined,
        ...data.settings,
        ...explicit,
        deck_timers: { ...(combined.deck_timers || {}), ...(data.settings.deck_timers || {}), ...explicitTimers }
      };
      applyServerSettings(combined);
      saveLocalSettings(combined);
      saveAndroidBridgeSettings(combined);
      ankiLog('DATA', 'SETTINGS', 'SETTINGS_SYNCED_FROM_SERVER', combined);
      if (typeof onUpdateCallback === 'function') onUpdateCallback(combined);
    }
  } catch (err) {
    ankiLog('INFO', 'NET', 'SETTINGS_SYNC_OFFLINE', { err: String(err) });
  }
}

function applyServerSettings(s) {
  if (s.deck_timers && typeof s.deck_timers === 'object') localStorage.setItem('anki_deck_timers', JSON.stringify(s.deck_timers));
  if (s.timer_duration !== undefined) localStorage.setItem('anki_timer_duration', String(s.timer_duration));
  if (s.session_target_min !== undefined) localStorage.setItem('anki_session_target_min', String(s.session_target_min));
  if (s.furigana_mode) localStorage.setItem('anki_furigana_mode', s.furigana_mode);
  if (s.front_font_size) localStorage.setItem('anki_front_font_size', String(s.front_font_size));
  if (s.back_font_size) localStorage.setItem('anki_back_font_size', String(s.back_font_size));
  if (Array.isArray(s.collapsed_decks)) localStorage.setItem('anki_collapsed_decks', JSON.stringify(s.collapsed_decks));
}

export function persistSetting(localKey, value) {
  const remoteKey = KEY_MAP[localKey] || localKey;
  if (typeof value === 'object') localStorage.setItem(localKey, JSON.stringify(value));
  else localStorage.setItem(localKey, String(value));

  const snap = getLocalSettingsSnapshot();
  saveLocalSettings(snap);
  saveAndroidBridgeSettings(snap);

  _pendingUpdates[remoteKey] = value;
  if (_syncTimeout) clearTimeout(_syncTimeout);
  _syncTimeout = setTimeout(() => flushPendingSettings(), 300);
}

export async function flushPendingSettings() {
  if (Object.keys(_pendingUpdates).length === 0) return;
  const payload = { ..._pendingUpdates };
  _pendingUpdates = {};
  try {
    const res = await fetch('/api/anki/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    ankiLog('DATA', 'SETTINGS', 'SETTINGS_PERSISTED_TO_SERVER', { payload, status: data.status });
  } catch (err) {
    ankiLog('WARN', 'NET', 'SETTINGS_PERSIST_FAILED', { err: String(err), payload });
  }
}
