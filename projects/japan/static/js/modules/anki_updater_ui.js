// static/js/modules/anki_updater_ui.js — Update Modal DOM Rendering
// Strictly <= 200 lines, <= 100 cols invariant.

const get = (id) => document.getElementById(id);

export function renderAppVersion(version) {
  document.querySelectorAll('.anki-version-badge').forEach((el) => {
    el.innerText = version;
  });
  const headerBtn = get('ankiHeaderVersionBtn');
  if (headerBtn) headerBtn.innerText = version;
  const curVerEl = get('ankiUpdateCurrentVersion');
  if (curVerEl) curVerEl.innerText = version;
  const settingsVer = get('ankiSettingsVersionText');
  if (settingsVer) settingsVer.innerText = `Versione corrente: ${version}`;
  const footerVer = get('ankiFooterVersionText');
  if (footerVer) footerVer.innerText = `Japan Mastery Web ${version}`;
}

export function setOfflineStatus() {
  const statusEl = get('ankiUpdateStatusText');
  if (statusEl) {
    statusEl.innerHTML =
      '<span class="text-amber-400 font-bold">' +
      '📴 Sei offline. Gli aggiornamenti richiedono connessione.</span>';
  }
  const actionContainer = get('ankiUpdateActionArea');
  if (actionContainer) actionContainer.innerHTML = '';
  const btnCheck = get('ankiBtnCheckUpdates');
  if (btnCheck) btnCheck.disabled = false;
}

export function setCheckingStatus() {
  const statusEl = get('ankiUpdateStatusText');
  if (statusEl) {
    statusEl.innerHTML =
      '<span class="animate-spin inline-block mr-1.5">⏳</span> ' +
      'Controllo disponibilità nuova versione...';
  }
  const btnCheck = get('ankiBtnCheckUpdates');
  if (btnCheck) btnCheck.disabled = true;
}

export function renderChangelog(changelog) {
  const container = get('ankiUpdateChangelog');
  if (!container || !Array.isArray(changelog)) return;
  container.innerHTML = changelog.map((item) => `
    <li class="flex items-start gap-2 text-xs text-neutral-300">
      <span class="text-[#42A5F5] font-bold">•</span>
      <span>${item}</span>
    </li>
  `).join('');
}

export function renderUpdateAvailable(version) {
  const statusEl = get('ankiUpdateStatusText');
  if (statusEl) {
    statusEl.innerHTML =
      `<span class="text-amber-400 font-bold">🎉 Nuova versione disponibile: ${version}</span>`;
  }
  const actionContainer = get('ankiUpdateActionArea');
  if (actionContainer) {
    actionContainer.innerHTML = `
      <button onclick="window.ankiApplyUpdate()"
        class="w-full py-3 bg-gradient-to-r from-[#2196F3] to-[#1E88E5] ` +
        `hover:from-[#1E88E5] hover:to-[#1976D2] text-white font-bold text-xs ` +
        `uppercase tracking-wider rounded-xl shadow-lg transition tap-press ` +
        `active:scale-95 flex items-center justify-center gap-2 border border-blue-400/40">
        <span>⚡ Aggiorna Adesso (${version})</span>
      </button>
    `;
  }
}

export function renderUpToDate(version) {
  const statusEl = get('ankiUpdateStatusText');
  if (statusEl) {
    statusEl.innerHTML =
      `<span class="text-emerald-400 font-bold">` +
      `✅ Sei all'ultima versione disponibile (${version})</span>`;
  }
  const actionContainer = get('ankiUpdateActionArea');
  if (actionContainer) {
    actionContainer.innerHTML = `
      <button onclick="window.ankiApplyUpdate()"
        class="w-full py-2.5 bg-white/5 hover:bg-white/10 text-neutral-300 ` +
        `font-bold text-xs rounded-xl transition tap-press active:scale-95 ` +
        `border border-white/10 flex items-center justify-center gap-2">
        <span>🔄 Ricarica & Sincronizza Forzato</span>
      </button>
    `;
  }
}

export function renderUpdateError(errMsg) {
  const statusEl = get('ankiUpdateStatusText');
  if (statusEl) {
    statusEl.innerHTML =
      `<span class="text-red-400 font-bold">⚠️ ${errMsg || 'Errore di connessione'}</span>`;
  }
  const actionContainer = get('ankiUpdateActionArea');
  if (actionContainer) {
    actionContainer.innerHTML = `
      <button onclick="window.ankiApplyUpdate()"
        class="w-full py-2.5 bg-white/5 hover:bg-white/10 text-neutral-300 ` +
        `font-bold text-xs rounded-xl transition tap-press border border-white/10">
        Forza Ricarica Locale
      </button>
    `;
  }
}

export function setApplyingStatus() {
  const statusEl = get('ankiUpdateStatusText');
  if (statusEl) {
    statusEl.innerHTML =
      '<span class="animate-spin inline-block mr-1.5">⏳</span> ' +
      'Aggiornamento PWA e sincronizzazione...';
  }
  const actionContainer = get('ankiUpdateActionArea');
  if (actionContainer) {
    actionContainer.querySelectorAll('button').forEach((b) => {
      b.disabled = true;
      b.classList.add('opacity-50', 'pointer-events-none');
    });
  }
}

export function setApplyingOfflineError() {
  const actionContainer = get('ankiUpdateActionArea');
  if (actionContainer) {
    actionContainer.querySelectorAll('button').forEach((b) => {
      b.disabled = false;
      b.classList.remove('opacity-50', 'pointer-events-none');
    });
  }
  const statusEl = get('ankiUpdateStatusText');
  if (statusEl) {
    statusEl.innerHTML =
      '<span class="text-red-400 font-bold">⚠️ Impossibile aggiornare mentre sei offline.</span>';
  }
}

export function showGlobalBanner(text, autoHideMs = 0, isSpinner = false) {
  const banner = get('ankiGlobalUpdateBanner');
  const txt = get('ankiGlobalUpdateText');
  if (!banner || !txt) return;
  const icon = isSpinner
    ? '<span class="animate-spin inline-block mr-1.5">🔄</span>'
    : '';
  txt.innerHTML = `${icon}${text}`;
  banner.classList.remove('hidden');
  if (autoHideMs > 0) {
    setTimeout(() => {
      if (banner) banner.classList.add('hidden');
    }, autoHideMs);
  }
}

export function hideGlobalBanner() {
  const banner = get('ankiGlobalUpdateBanner');
  if (banner) banner.classList.add('hidden');
}

export function setHeaderUpdateBadge(version) {
  const btn = get('ankiHeaderVersionBtn');
  if (!btn) return;
  btn.classList.remove(
    'bg-emerald-500/20', 'hover:bg-emerald-500/30',
    'text-emerald-400', 'border-emerald-500/40'
  );
  btn.classList.add(
    'bg-amber-500/20', 'hover:bg-amber-500/30',
    'text-amber-400', 'border-amber-500/40', 'animate-pulse'
  );
  btn.innerText = `⚡ ${version}`;
}

