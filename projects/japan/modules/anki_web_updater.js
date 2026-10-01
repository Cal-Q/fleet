import { ankiLog } from './anki_logger.js';
import { flushPendingSettings } from './anki_web_persistence.js';

export const CURRENT_VERSION = 'v2.8.1';
export const CURRENT_BUILD = '20260926_v281';

const get = (id) => document.getElementById(id);

export function getAppVersion() {
  return { version: CURRENT_VERSION, build: CURRENT_BUILD };
}

export function renderAppVersion() {
  document.querySelectorAll('.anki-version-badge').forEach(el => {
    el.innerText = CURRENT_VERSION;
  });
  const headerBtn = get('ankiHeaderVersionBtn');
  if (headerBtn) headerBtn.innerText = CURRENT_VERSION;
  const curVerEl = get('ankiUpdateCurrentVersion');
  if (curVerEl) curVerEl.innerText = CURRENT_VERSION;
  const settingsVer = get('ankiSettingsVersionText');
  if (settingsVer) settingsVer.innerText = `Versione corrente: ${CURRENT_VERSION}`;
  const footerVer = get('ankiFooterVersionText');
  if (footerVer) footerVer.innerText = `Japan Mastery Web ${CURRENT_VERSION}`;
}

if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderAppVersion);
  } else {
    setTimeout(renderAppVersion, 0);
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
  const statusEl = get('ankiUpdateStatusText');
  const btnCheck = get('ankiBtnCheckUpdates');
  const actionContainer = get('ankiUpdateActionArea');
  const changelogContainer = get('ankiUpdateChangelog');

  if (!navigator.onLine) {
    _isChecking = false;
    if (statusEl) statusEl.innerHTML = '<span class="text-amber-400 font-bold">📴 Sei offline. Gli aggiornamenti richiedono connessione.</span>';
    if (actionContainer) actionContainer.innerHTML = '';
    if (btnCheck) btnCheck.disabled = false;
    return;
  }

  if (statusEl) statusEl.innerHTML = '<span class="animate-spin inline-block mr-1.5">⏳</span> Controllo disponibilità nuova versione...';
  if (btnCheck) btnCheck.disabled = true;

  try {
    let remoteData = null;
    try {
      const res = await fetch('/api/anki/version?t=' + Date.now(), { cache: 'no-store' });
      if (res.ok) remoteData = await res.json();
    } catch {}

    if (!remoteData) {
      const fallbackRes = await fetch('https://japan.calq.it/api/anki/version?t=' + Date.now(), { cache: 'no-store' });
      if (fallbackRes.ok) remoteData = await fallbackRes.json();
    }

    if (!remoteData || remoteData.status !== 'ok') {
      throw new Error('Impossibile contattare il server degli aggiornamenti');
    }

    const latestVer = remoteData.version || CURRENT_VERSION;
    const isNewer = compareVersions(latestVer, CURRENT_VERSION) > 0;

    if (changelogContainer && remoteData.changelog?.length > 0) {
      changelogContainer.innerHTML = remoteData.changelog.map(item => `
        <li class="flex items-start gap-2 text-xs text-neutral-300">
          <span class="text-[#42A5F5] font-bold">•</span>
          <span>${item}</span>
        </li>
      `).join('');
    }

    if (isNewer) {
      if (statusEl) statusEl.innerHTML = `<span class="text-amber-400 font-bold">🎉 Nuova versione disponibile: ${latestVer}</span>`;
      if (actionContainer) {
        actionContainer.innerHTML = `
          <button onclick="window.ankiApplyUpdate()" class="w-full py-3 bg-gradient-to-r from-[#2196F3] to-[#1E88E5] hover:from-[#1E88E5] hover:to-[#1976D2] text-white font-bold text-xs uppercase tracking-wider rounded-xl shadow-lg transition tap-press active:scale-95 flex items-center justify-center gap-2 border border-blue-400/40">
            <span>⚡ Aggiorna Adesso (${latestVer})</span>
          </button>
        `;
      }
      ankiLog('INFO', 'UPDATER', 'UPDATE_AVAILABLE', { current: CURRENT_VERSION, latest: latestVer });
    } else {
      if (statusEl) statusEl.innerHTML = `<span class="text-emerald-400 font-bold">✅ Sei all'ultima versione disponibile (${CURRENT_VERSION})</span>`;
      if (actionContainer) {
        actionContainer.innerHTML = `
          <button onclick="window.ankiApplyUpdate()" class="w-full py-2.5 bg-white/5 hover:bg-white/10 text-neutral-300 font-bold text-xs rounded-xl transition tap-press active:scale-95 border border-white/10 flex items-center justify-center gap-2">
            <span>🔄 Ricarica & Sincronizza Forzato</span>
          </button>
        `;
      }
      ankiLog('INFO', 'UPDATER', 'UP_TO_DATE', { version: CURRENT_VERSION });
    }
  } catch (err) {
    if (statusEl) statusEl.innerHTML = `<span class="text-red-400 font-bold">⚠️ ${err.message || 'Errore di connessione'}</span>`;
    if (actionContainer) {
      actionContainer.innerHTML = `
        <button onclick="window.ankiApplyUpdate()" class="w-full py-2.5 bg-white/5 hover:bg-white/10 text-neutral-300 font-bold text-xs rounded-xl transition tap-press border border-white/10">
          Forza Ricarica Locale
        </button>
      `;
    }
    ankiLog('WARN', 'UPDATER', 'CHECK_FAILED', { error: err.message });
  } finally {
    _isChecking = false;
    if (btnCheck) btnCheck.disabled = false;
  }
}

export async function applyUpdate() {
  if (_isApplyingUpdate) return;
  _isApplyingUpdate = true;
  const statusEl = get('ankiUpdateStatusText');
  const actionContainer = get('ankiUpdateActionArea');
  if (actionContainer) {
    actionContainer.querySelectorAll('button').forEach(b => {
      b.disabled = true;
      b.classList.add('opacity-50', 'pointer-events-none');
    });
  }

  if (!navigator.onLine) {
    _isApplyingUpdate = false;
    if (actionContainer) {
      actionContainer.querySelectorAll('button').forEach(b => {
        b.disabled = false;
        b.classList.remove('opacity-50', 'pointer-events-none');
      });
    }
    if (statusEl) statusEl.innerHTML = '<span class="text-red-400 font-bold">⚠️ Impossibile aggiornare mentre sei offline.</span>';
    return;
  }

  if (statusEl) statusEl.innerHTML = '<span class="animate-spin inline-block mr-1.5">⏳</span> Aggiornamento PWA e sincronizzazione...';
  ankiLog('ACTION', 'UPDATER', 'APPLYING_UPDATE', {});

  try { await flushPendingSettings(); } catch {}

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
