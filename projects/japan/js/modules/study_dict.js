// static/js/modules/study_dict.js — Manual JMdict Lookup & Ingestion
// Strictly <= 200 lines invariant.

import { loadStudyStatus } from './study.js';

export async function searchManualVocab() {
  const input = document.getElementById('vocabSearchInput');
  const resDiv = document.getElementById('vocabSearchResults');
  if (!input || !resDiv || !input.value.trim()) return;
  resDiv.innerHTML = '<div class="text-xs font-mono text-neutral-400 py-1">Ricerca JMdict in corso...</div>';
  try {
    const res = await fetch(`/api/dict/search?q=${encodeURIComponent(input.value.trim())}`);
    const data = await res.json();
    if (!data.results?.length) {
      resDiv.innerHTML = '<div class="text-xs font-mono text-neutral-500 py-1">Nessun lemma trovato.</div>';
      return;
    }
    resDiv.innerHTML = data.results.slice(0, 5).map(r => `
      <div class="p-2 border-b border-black/5 flex items-center justify-between text-xs">
        <div>
          <b class="jp-font">${r.kanji || r.kana}</b> <span class="text-neutral-500 font-mono text-[11px] ml-1">(${r.kana})</span>
          <p class="text-[11px] text-neutral-600 truncate max-w-sm" title="${(r.glossary?.join(', ') || '').replace(/"/g, '&quot;')}">${r.glossary?.join(', ')}</p>
        </div>
        <button onclick="window.addManualWord('${r.kana}', '${(r.glossary?.[0] || '').replace(/'/g, "\\'")}')" class="px-2 py-1 text-[10px] font-mono font-bold uppercase border border-black hover:bg-black hover:text-white transition">+ Inserisci</button>
      </div>
    `).join('');
  } catch (err) {
    resDiv.innerHTML = `<div class="text-xs font-mono text-[#E63920]">Errore: ${err.message}</div>`;
  }
}

export async function addManualWord(kana, meaning) {
  try {
    const res = await fetch('/api/study/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category: 'vocab', item_id: kana, payload: { word: kana, reading: kana, meaning } })
    });
    const data = await res.json();
    alert(data.status === 'ok' ? 'Lemma aggiunto con successo!' : 'Errore: ' + (data.detail || 'Operazione fallita'));
    loadStudyStatus();
  } catch (e) {
    alert('Errore di rete: ' + e.message);
  }
}

window.searchManualVocab = searchManualVocab;
window.addManualWord = addManualWord;
