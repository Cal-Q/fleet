// static/js/modules/anki_log_viewer.js — UI Diagnostic Log Viewer Modal
// Strictly <= 200 lines invariant.
import { getLogs, clearLogs, exportLogsAsJson, sendLogsToServer } from './anki_logger.js';

let _activeFilter = 'ALL';
let _searchQuery = '';

const get = id => document.getElementById(id);

export function toggleLogViewer(forceState = null) {
  const modal = get('ankiLogModal');
  if (!modal) return;
  const isHidden = modal.classList.contains('hidden');
  const shouldOpen = forceState !== null ? forceState : isHidden;
  modal.classList.toggle('hidden', !shouldOpen);
  if (shouldOpen) {
    renderLogList();
    window.ankiOnLogUpdate = () => { if (!modal.classList.contains('hidden')) renderLogList(); };
  } else {
    window.ankiOnLogUpdate = null;
  }
}

export function setLogFilter(filter) {
  _activeFilter = filter;
  updateFilterButtons();
  renderLogList();
}

export function setLogSearch(query) {
  _searchQuery = query;
  renderLogList();
}

function updateFilterButtons() {
  const cats = ['ALL', 'DECK', 'CARD', 'NET', 'ERROR'];
  cats.forEach(c => {
    const btn = get(`btnLogFilter_${c}`);
    if (btn) {
      const active = _activeFilter === c;
      btn.className = `px-2 py-1 rounded text-[10px] font-mono font-bold transition tap-press ${
        active ? 'bg-[#2196F3] text-white shadow' : 'bg-[#2A2A2A] text-neutral-400 hover:text-white'
      }`;
    }
  });
}

export function renderLogList() {
  const container = get('ankiLogListContainer');
  const countBadge = get('ankiLogCountBadge');
  if (!container) return;

  const logs = getLogs(_activeFilter, _searchQuery);
  if (countBadge) countBadge.innerText = `${logs.length} eventi`;

  if (!logs.length) {
    container.innerHTML = `<div class="p-6 text-center text-neutral-500 font-mono text-xs">Nessun evento registrato con i filtri correnti.</div>`;
    return;
  }

  const badgeColor = {
    ERROR: 'bg-red-900/60 text-red-300 border-red-700',
    WARN: 'bg-amber-900/60 text-amber-300 border-amber-700',
    ACTION: 'bg-blue-900/60 text-blue-300 border-blue-700',
    DATA: 'bg-emerald-900/60 text-emerald-300 border-emerald-700',
    INFO: 'bg-purple-900/60 text-purple-300 border-purple-700'
  };

  const reversed = [...logs].reverse();
  container.innerHTML = reversed.map(l => {
    const t = l.time.split('T')[1].replace('Z', '');
    const color = badgeColor[l.level] || 'bg-neutral-800 text-neutral-300 border-neutral-700';
    const jsonStr = JSON.stringify(l.det, null, 2);
    return `
      <div class="p-2 bg-[#161616] border border-[#2A2A2A] rounded-lg space-y-1 font-mono text-[11px]">
        <div class="flex items-center justify-between gap-1">
          <div class="flex items-center gap-1.5 min-w-0">
            <span class="px-1.5 py-0.2 rounded border text-[9px] font-bold ${color}">${l.level}</span>
            <span class="text-neutral-400 text-[10px]">[${l.cat}]</span>
            <span class="text-white font-bold truncate">${l.act}</span>
          </div>
          <span class="text-neutral-500 text-[10px] flex-shrink-0">${t}</span>
        </div>
        ${Object.keys(l.det || {}).length > 0 ? `
          <pre class="bg-[#111111] p-1.5 rounded border border-[#222222] text-[10px] text-neutral-300 overflow-x-auto max-h-24 overscroll-contain">${escapeHtml(jsonStr)}</pre>
        ` : ''}
      </div>
    `;
  }).join('');
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

export async function copyLogsToClipboard() {
  const text = exportLogsAsJson();
  try {
    await navigator.clipboard.writeText(text);
    showLogToast('✅ Log copiati negli appunti');
  } catch {
    showLogToast('❌ Errore copia appunti');
  }
}

export async function handleSendLogs() {
  showLogToast('⏳ Invio log al server...');
  const res = await sendLogsToServer();
  if (res.ok) showLogToast('✅ Log inviati al server con successo');
  else showLogToast('❌ Invio fallito (offline)');
}

export function handleClearLogs() {
  if (confirm('Cancellare tutti i log diagnostici?')) {
    clearLogs();
    renderLogList();
    showLogToast('🗑️ Registro pulito');
  }
}

function showLogToast(msg) {
  const toast = get('ankiLogToast');
  if (!toast) return;
  toast.innerText = msg;
  toast.classList.remove('hidden');
  setTimeout(() => toast.classList.add('hidden'), 2500);
}

Object.assign(window, {
  ankiToggleLogViewer: toggleLogViewer,
  ankiSetLogFilter: setLogFilter,
  ankiSetLogSearch: setLogSearch,
  ankiCopyLogs: copyLogsToClipboard,
  ankiSendLogsAction: handleSendLogs,
  ankiClearLogsAction: handleClearLogs
});
