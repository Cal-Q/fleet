// static/js/modules/study.js — Group Batch Staging & Progressive Disclosure (Zero Modals)
// Strictly <= 200 lines invariant.

import { renderKanjiPreview, renderVocabPreview, renderGrammarPreview } from './study_render.js';

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
    const res = await fetch('/api/study/next?t=' + Date.now());
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

export function switchStudyBranch(b) {
  ['kanji', 'vocab', 'grammar'].forEach(x => {
    document.getElementById(`leaf_${x}`)?.classList.toggle('hidden', x !== b);
    const btn = document.getElementById(`branch_btn_${x}`);
    if (btn) {
      btn.classList.toggle('bg-white', x === b); btn.classList.toggle('shadow-sm', x === b);
      btn.classList.toggle('bg-[#FAF8F5]', x !== b); btn.classList.toggle('opacity-70', x !== b);
    }
  });
  loadUpcomingPreviews();
}
export function toggleDrawer(id) { document.getElementById(id)?.classList.toggle('open'); }


export async function syncBatchGroup(type) {
  if (isSyncing) return;
  const batches = { kanji: nextKanjiBatch, vocab: nextVocabBatch, grammar: nextGrammarBatch };
  const currentBatch = batches[type] || [];
  if (!currentBatch.length) return alert(`Nessun elemento ${type} disponibile.`);
  if (type === 'grammar' && currentBatch.some(g => g.is_locked || (g.unreviewed_vocab_count || g.missing_vocab?.length || 0) > 0)) {
    alert('Aggiunta bloccata: devi prima studiare tutti i vocaboli contrassegnati con 🔴 REQ nella sezione Vocabolario.');
    switchStudyBranch('vocab');
    return;
  }

  isSyncing = true;
  const btnId = `btnSync${type.charAt(0).toUpperCase() + type.slice(1)}`;
  const btn = document.getElementById(btnId);
  const origBtnText = btn ? btn.innerText : '';
  if (btn) {
    btn.disabled = true;
    btn.classList.add('opacity-70', 'cursor-wait');
    btn.innerText = `⏳ In corso (${currentBatch.length})...`;
  }

  const syncBar = document.getElementById('studyInlineSyncBar');
  const syncMsg = document.getElementById('studyInlineSyncMsg');
  if (syncBar) syncBar.classList.remove('hidden');
  if (syncMsg) syncMsg.innerText = `⏳ 1/3 Staging ${type.toUpperCase()} in corso (Anki Engine)...`;

  const progTimer = setTimeout(() => {
    if (syncMsg && isSyncing) syncMsg.innerText = `🔄 2/3 Sincronizzazione SQLite & Push AnkiWeb...`;
  }, 1200);

  try {
    const res = await fetch('/api/study/add_batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category: type, items: currentBatch })
    });
    clearTimeout(progTimer);
    const result = await res.json();
    if (result.status === 'ok' || result.status === 'warning') {
      const ankiInfo = result.anki_stats?.total ? ` (Anki: ${result.anki_stats.new ?? 0} nuove, ${result.anki_stats.total} totali)` : '';
      if (syncMsg) syncMsg.innerText = `✅ Completato: ${result.message || 'Sincronizzato'}${ankiInfo}`;
      if (btn) btn.innerText = `✅ Sincronizzato!`;
      await loadStudyStatus();
      setTimeout(() => {
        if (syncBar) syncBar.classList.add('hidden');
        if (btn) {
          btn.disabled = false;
          btn.classList.remove('opacity-70', 'cursor-wait');
          const nextCount = (type === 'vocab' ? 20 : 5);
          btn.innerText = `Sincronizza Gruppo (${nextCount}) →`;
        }
        isSyncing = false;
      }, 1500);
    } else {
      if (syncMsg) syncMsg.innerText = `❌ Errore: ${result.detail || result.message || 'Operazione fallita'}`;
      if (btn) {
        btn.innerText = `❌ Fallito`;
        setTimeout(() => {
          if (btn) { btn.disabled = false; btn.classList.remove('opacity-70', 'cursor-wait'); btn.innerText = origBtnText; }
        }, 2500);
      }
      setTimeout(() => { if (syncBar) syncBar.classList.add('hidden'); isSyncing = false; }, 3000);
    }
  } catch (err) {
    clearTimeout(progTimer);
    if (syncMsg) syncMsg.innerText = `❌ Errore di rete: ${err.message}`;
    if (btn) {
      btn.innerText = `❌ Errore di rete`;
      setTimeout(() => {
        if (btn) { btn.disabled = false; btn.classList.remove('opacity-70', 'cursor-wait'); btn.innerText = origBtnText; }
      }, 2500);
    }
    setTimeout(() => { if (syncBar) syncBar.classList.add('hidden'); isSyncing = false; }, 3000);
  }
}

export { searchManualVocab, addManualWord } from './study_dict.js';

