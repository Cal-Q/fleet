// static/js/modules/study.js — Group Batch Staging & Progressive Disclosure (Zero Modals)
// Strictly <= 200 lines invariant.

let nextKanjiBatch = [];
let nextVocabBatch = [];
let nextGrammarBatch = [];
let isSyncing = false;

export async function loadStudyStatus() {
  try {
    const p1 = fetch('/api/study/status').then(r => r.json()).then(data => {
      const setTxt = (id, v) => { const el = document.getElementById(id); if (el && v !== undefined) el.innerText = v; };
      if (data.today) { setTxt('countKanjiAdded', data.today.kanji ?? 0); setTxt('countVocabAdded', data.today.vocab ?? 0); setTxt('countGrammarAdded', data.today.grammar ?? 0); }
    });
    await Promise.all([p1, loadUpcomingPreviews()]);
  } catch (err) {
    console.error('Error loading study status:', err);
  }
}

export async function loadUpcomingPreviews() {
  try {
    const res = await fetch('/api/study/next');
    const data = await res.json();

    nextKanjiBatch = data.kanji || [];
    nextVocabBatch = data.vocab || [];
    nextGrammarBatch = (data.grammar && data.grammar.length > 0) ? data.grammar : (data.locked_grammar || []);

    renderKanjiPreview(nextKanjiBatch);
    renderVocabPreview(nextVocabBatch);
    renderGrammarPreview(nextGrammarBatch);
  } catch (err) {
    console.error('Error loading upcoming previews:', err);
  }
}

function renderKanjiPreview(items) {
  const container = document.getElementById('previewKanjiContainer');
  if (!container) return;
  if (!items.length) {
    container.innerHTML = '<div class="text-xs text-neutral-400 py-2">Nessun kanji in coda.</div>';
    return;
  }
  container.innerHTML = items.map(k => `
    <div class="p-2 border border-black/10 bg-white space-y-1">
      <div class="flex items-center justify-between text-[10px] font-mono text-neutral-500">
        <span>#${k.id || ''}</span>
        <span class="font-bold text-[#E63920]">${k.jlpt_level || 'N/A'}</span>
      </div>
      <div class="text-2xl font-bold text-center jp-font py-0.5">${k.kanji}</div>
      <div class="text-[11px] font-mono text-center truncate text-neutral-700" title="${k.keyword || ''}">${k.keyword || ''}</div>
    </div>
  `).join('');
}

function renderVocabPreview(items) {
  const container = document.getElementById('previewVocabContainer');
  if (!container) return;
  if (!items.length) {
    container.innerHTML = '<div class="text-xs text-neutral-400 py-2">Nessun vocabolo in coda.</div>';
    return;
  }
  container.innerHTML = items.map((v, i) => `
    <div class="flex items-center justify-between py-1.5 px-2 border-b border-black/5 text-xs">
      <div class="flex items-baseline gap-2 truncate" title="${v.word || v.kana || ''}">
        <span class="text-[10px] font-mono text-neutral-400">${String(i + 1).padStart(2, '0')}</span>
        <span class="jp-font font-bold text-[#111111]">${v.word || v.kana || ''}</span>
        ${v.reading && v.reading !== v.word ? `<span class="text-[10px] font-mono text-neutral-400">(${v.reading})</span>` : ''}
        ${v.required_by_grammar ? '<span class="text-[9px] font-mono px-1 py-0.2 bg-[#EEF7F1] text-[#1E5233] border border-[#1E5233]/20">req</span>' : ''}
      </div>
      <span class="font-mono text-[11px] text-neutral-600 truncate max-w-[200px]" title="${v.meaning || v.english || ''}">${v.meaning || v.english || ''}</span>
    </div>
  `).join('');
}

function renderGrammarPreview(items) {
  const container = document.getElementById('previewGrammarContainer');
  if (!container) return;
  if (!items.length) {
    container.innerHTML = '<div class="text-xs text-neutral-400 py-2">Nessun punto grammaticale in coda.</div>';
    return;
  }
  container.innerHTML = items.map(g => {
    const isLocked = g.unreviewed_vocab_count > 0;
    const cBadge = g.mext_cluster ? `<span class="text-[9px] font-mono px-1 py-0.5 bg-[#EEF7F1] text-[#1E5233] border border-[#1E5233]/20 font-bold">${g.mext_cluster.split(':')[0]}</span>` : '';
    const samples = (g.unreviewed_vocab_samples || []).join(', ');
    const lockInfo = isLocked ? `
      <div class="mt-1 p-1.5 bg-[#FDF1EF] border border-[#C23B22]/20 text-[10px] font-mono flex items-center justify-between gap-1">
        <span class="text-[#C23B22] truncate" title="Mancano: ${samples || g.unreviewed_vocab_count + ' vocaboli'}">🔒 <b>Coperta (Sospesa):</b> mancano: <b>${samples || g.unreviewed_vocab_count + ' vocaboli'}</b></span>
        <button onclick="switchStudyBranch('vocab')" class="flex-shrink-0 text-[9px] px-1 py-0.5 bg-[#1E2C3A] text-white font-bold hover:bg-black uppercase">Vocaboli →</button>
      </div>` : `
      <div class="mt-1 px-1.5 py-0.5 bg-[#EEF7F1] border border-[#264332]/20 text-[10px] font-mono text-[#264332] font-bold">
        ✅ Vocaboli Noti: si attiva subito come Nuova in Anki
      </div>`;
    return `
    <div class="p-2.5 border border-black/10 bg-white space-y-1">
      <div class="flex items-center justify-between text-xs">
        <span class="font-bold jp-font text-sm text-[#111111]">${g.title}</span>
        <div class="flex items-center gap-1">${cBadge}<span class="text-[10px] font-mono px-1.5 py-0.5 bg-neutral-100 text-neutral-600">${g.level}</span></div>
      </div>
      <div class="text-[11px] text-neutral-600 italic font-mono">${g.meaning}</div>
      ${lockInfo}
    </div>`;
  }).join('');
}

export function switchStudyBranch(branch) {
  ['kanji', 'vocab', 'grammar'].forEach(b => {
    const leaf = document.getElementById(`leaf_${b}`);
    const btn = document.getElementById(`branch_btn_${b}`);
    if (leaf) leaf.classList.toggle('hidden', b !== branch);
    if (btn) {
      btn.classList.toggle('bg-white', b === branch);
      btn.classList.toggle('shadow-sm', b === branch);
      btn.classList.toggle('bg-[#FAF8F5]', b !== branch);
      btn.classList.toggle('opacity-70', b !== branch);
    }
  });
}
export function toggleDrawer(id) { const el = document.getElementById(id); if (el) el.classList.toggle('open'); }

export async function syncBatchGroup(type) {
  if (isSyncing) return;
  const batches = { kanji: nextKanjiBatch, vocab: nextVocabBatch, grammar: nextGrammarBatch };
  const currentBatch = batches[type] || [];
  if (!currentBatch.length) {
    alert(`Nessun elemento ${type} disponibile nel batch.`);
    return;
  }

  isSyncing = true;
  const syncBar = document.getElementById('studyInlineSyncBar');
  const syncMsg = document.getElementById('studyInlineSyncMsg');
  if (syncBar) syncBar.classList.remove('hidden');
  if (syncMsg) syncMsg.innerText = `Sincronizzazione ${type.toUpperCase()} su relay in corso (Rust AnkiWeb Engine)...`;

  try {
    const res = await fetch('/api/study/add_batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category: type, items: currentBatch })
    });
    const result = await res.json();
    if (result.status === 'ok') {
      if (syncMsg) syncMsg.innerText = `✅ Completato: ${result.message || 'Sincronizzato con successo'}`;
      await loadStudyStatus();
      setTimeout(() => { if (syncBar) syncBar.classList.add('hidden'); isSyncing = false; }, 800);
    } else {
      if (syncMsg) syncMsg.innerText = `❌ Errore: ${result.detail || result.message || 'Operazione fallita'}`;
      setTimeout(() => { if (syncBar) syncBar.classList.add('hidden'); isSyncing = false; }, 3000);
    }
  } catch (err) {
    if (syncMsg) syncMsg.innerText = `❌ Errore di rete: ${err.message}`;
    setTimeout(() => { if (syncBar) syncBar.classList.add('hidden'); isSyncing = false; }, 3000);
  }
}

export async function searchManualVocab() {
  const input = document.getElementById('vocabSearchInput');
  const resDiv = document.getElementById('vocabSearchResults');
  if (!input || !resDiv || !input.value.trim()) return;
  resDiv.innerHTML = '<div class="text-xs font-mono text-neutral-400 py-1">Ricerca JMdict in corso...</div>';
  try {
    const res = await fetch(`/api/dict/search?q=${encodeURIComponent(input.value.trim())}`);
    const data = await res.json();
    if (!data.results?.length) { resDiv.innerHTML = '<div class="text-xs font-mono text-neutral-500 py-1">Nessun lemma trovato.</div>'; return; }
    resDiv.innerHTML = data.results.slice(0, 5).map(r => `
      <div class="p-2 border-b border-black/5 flex items-center justify-between text-xs">
        <div>
          <b class="jp-font">${r.kanji || r.kana}</b> <span class="text-neutral-500 font-mono text-[11px] ml-1">(${r.kana})</span>
          <p class="text-[11px] text-neutral-600 truncate max-w-sm" title="${(r.glossary?.join(', ') || '').replace(/"/g, '&quot;')}">${r.glossary?.join(', ')}</p>
        </div>
        <button onclick="window.addManualWord('${r.kana}', '${(r.glossary?.[0] || '').replace(/'/g, "\\'")}')" class="px-2 py-1 text-[10px] font-mono font-bold uppercase border border-black hover:bg-black hover:text-white transition">+ Inserisci</button>
      </div>
    `).join('');
  } catch (err) { resDiv.innerHTML = `<div class="text-xs font-mono text-[#E63920]">Errore: ${err.message}</div>`; }
}

window.addManualWord = async (kana, meaning) => {
  try {
    const res = await fetch('/api/study/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category: 'vocab', item_id: kana, payload: { word: kana, reading: kana, meaning } })
    });
    const data = await res.json();
    alert(data.status === 'ok' ? 'Lemma aggiunto con successo!' : 'Errore: ' + (data.detail || 'Operazione fallita'));
    loadStudyStatus();
  } catch (e) { alert('Errore di rete: ' + e.message); }
};
