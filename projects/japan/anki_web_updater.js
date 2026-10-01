// static/js/modules/anki_web_updater.js — PWA Version Checker & Auto-Updater
// Strictly <= 200 lines, <= 100 cols invariant.

import { ankiLog } from './anki_logger.js';
import { flushPendingSettings } from './anki_web_persistence.js';
import {
  renderAppVersion as renderAppVersionUi,
  setOfflineStatus,
  setCheckingStatus,
  renderChangelog,
  renderUpdateAvailable,
  renderUpToDate,
  renderUpdateError,
  setApplyingStatus,
  setApplyingOfflineError,
  showGlobalBanner,
  setHeaderUpdateBadge
} from './anki_updater_ui.js';

export const CURRENT_VERSION = 'v2.9.6';
export const CURRENT_BUILD = '20260927_v296';

const get = (id) => document.getElementById(id);

export function getAppVersion() {
  return { version: CURRENT_VERSION, build: CURRENT_BUILD };
}

export function renderAppVersion() {
  renderAppVersionUi(CURRENT_VERSION);
}

if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      renderAppVersion();
      initSwUpdateListener();
      setTimeout(() => checkUpdates(false), 2500);
    });
  } else {
    setTimeout(() => {
      renderAppVersion();
      initSwUpdateListener();
      setTimeout(() => checkUpdates(false), 2500);
    }, 0);
  }
}

export function openUpdateModal() {
  const modal = get('ankiUpdateModal');
  if (!modal) return;
  modal.classList.remove('hidden');
  renderAppVersion();
  checkUpdates(false);
}

export function closeUpdateModal() {
  const modal = get('ankiUpdateModal');
  if (modal) modal.classList.add('hidden');
}

let _isChecking = false;
let _isApplyingUpdate = false;

export async function checkUpdates(interactive = true) {
  if (_isChecking) return;
  _isChecking = true;
  const btnCheck = get('ankiBtnCheckUpdates');

  if (!navigator.onLine) {
    _isChecking = false;
    setOfflineStatus();
    return;
  }

  setCheckingStatus();

  try {
    let remoteData = null;
    try {
      const res = await fetch('/api/anki/version?t=' + Date.now(), { cache: 'no-store' });
      if (res.ok) remoteData = await res.json();
    } catch {}

    if (!remoteData) {
      const fbUrl = 'https://japan.calq.it/api/anki/version?t=' + Date.now();
      const fallbackRes = await fetch(fbUrl, { cache: 'no-store' });
      if (fallbackRes.ok) remoteData = await fallbackRes.json();
    }

    if (!remoteData || remoteData.status !== 'ok') {
      throw new Error('Impossibile contattare il server degli aggiornamenti');
    }

    const latestVer = remoteData.version || CURRENT_VERSION;
    const isNewer = compareVersions(latestVer, CURRENT_VERSION) > 0;

    if (remoteData.changelog?.length > 0) {
      renderChangelog(remoteData.changelog);
    }

    if (isNewer) {
      renderUpdateAvailable(latestVer);
      setHeaderUpdateBadge(latestVer);
      showGlobalBanner(
        `Nuova versione ${latestVer} disponibile! Tocca per aggiornare.`,
        8000, false
      );
      ankiLog('INFO', 'UPDATER', 'UPDATE_AVAILABLE', {
        current: CURRENT_VERSION,
        latest: latestVer
      });
    } else {
      renderUpToDate(CURRENT_VERSION);
      ankiLog('INFO', 'UPDATER', 'UP_TO_DATE', { version: CURRENT_VERSION });
    }
  } catch (err) {
    renderUpdateError(err.message);
    ankiLog('WARN', 'UPDATER', 'CHECK_FAILED', { error: err.message });
  } finally {
    _isChecking = false;
    if (btnCheck) btnCheck.disabled = false;
  }
}

export async function applyUpdate() {
  if (_isApplyingUpdate) return;
  _isApplyingUpdate = true;

  if (!navigator.onLine) {
    _isApplyingUpdate = false;
    setApplyingOfflineError();
    return;
  }

  setApplyingStatus();
  showGlobalBanner('Aggiornamento versione PWA in corso... Ricarica...', 0, true);
  ankiLog('ACTION', 'UPDATER', 'APPLYING_UPDATE', {});

  try {
    await flushPendingSettings();
  } catch {}

  try {
    if ('serviceWorker' in navigator) {
      const reg = await navigator.serviceWorker.getRegistration();
      if (reg) {
        await reg.update();
        if (reg.waiting) reg.waiting.postMessage({ type: 'SKIP_WAITING' });
      }
    }
  } catch {}

  setTimeout(() => {
    window.location.reload();
  }, 400);
}

export function initSwUpdateListener() {
  if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return;
  navigator.serviceWorker.ready.then((reg) => {
    reg.addEventListener('updatefound', () => {
      const newSw = reg.installing;
      if (!newSw) return;
      showGlobalBanner('Download nuova versione PWA...', 0, true);
      newSw.addEventListener('statechange', () => {
        if (newSw.state === 'installed' && navigator.serviceWorker.controller) {
          showGlobalBanner('Nuova versione pronta! Applicazione...', 1500, false);
          setTimeout(() => applyUpdate(), 1000);
        }
      });
    });
  }).catch(() => {});

  navigator.serviceWorker.addEventListener('controllerchange', () => {
    showGlobalBanner('Versione aggiornata! Ricarica in corso...', 1000, false);
    setTimeout(() => window.location.reload(), 500);
  });
}

function compareVersions(v1, v2) {
  const p1 = (v1 || '').replace(/^v/, '').split('.').map(Number);
  const p2 = (v2 || '').replace(/^v/, '').split('.').map(Number);
  for (let i = 0; i < Math.max(p1.length, p2.length); i++) {
    const num1 = p1[i] || 0;
    const num2 = p2[i] || 0;
    if (num1 > num2) return 1;
    if (num1 < num2) return -1;
  }
  return 0;
}

Object.assign(window, {
  ankiOpenUpdateModal: openUpdateModal,
  ankiCloseUpdateModal: closeUpdateModal,
  ankiCheckUpdates: () => checkUpdates(true),
  ankiApplyUpdate: applyUpdate
});

