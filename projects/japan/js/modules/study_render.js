// static/js/modules/study_render.js — UI Renderers for Study Preview Stages
// Strictly <= 200 lines invariant.

export function renderKanjiPreview(items) {
  const container = document.getElementById('previewKanjiContainer');
  if (!container) return;
  if (!items.length) {
    container.innerHTML = '<div class="text-xs text-neutral-400 py-2">Nessun kanji in coda.</div>';
    return;
  }
  container.innerHTML = items.map(k => `
    <div class="p-2 border border-black/10 bg-white space-y-1 animate-info-fade">
      <div class="flex items-center justify-between text-[10px] font-mono text-neutral-500">
        <span>#${k.id || ''}</span>
        <span class="font-bold text-[#E63920]">${k.jlpt_level || 'N/A'}</span>
      </div>
      <div class="text-2xl font-bold text-center jp-font py-0.5">${k.kanji}</div>
      <div class="text-[11px] font-mono text-center truncate text-neutral-700" title="${k.keyword || ''}">${k.keyword || ''}</div>
    </div>
  `).join('');
}

export function renderVocabPreview(items) {
  const container = document.getElementById('previewVocabContainer');
  if (!container) return;
  if (!items.length) {
    container.innerHTML = '<div class="text-xs text-neutral-400 py-2">Nessun vocabolo in coda.</div>';
    return;
  }
  container.innerHTML = items.map((v, i) => {
    let reqBadge = '';
    if (v.req_type === 'blocking') {
      reqBadge = `<span class="text-[9px] font-mono px-1 py-0.5 bg-[#FDF1EF] text-[#C23B22] border border-[#C23B22]/30 font-bold" title="${v.source || 'Prerequisito bloccante'}">🔴 REQ</span>`;
    } else if (v.req_type === 'consolidation') {
      reqBadge = `<span class="text-[9px] font-mono px-1 py-0.5 bg-[#EEF7F1] text-[#1E5233] border border-[#1E5233]/20 font-bold" title="${v.source || 'Consolidamento'}">🟢 REQ</span>`;
    }
    return `
    <div class="flex items-center justify-between py-1.5 px-2 border-b border-black/5 text-xs animate-info-fade">
      <div class="flex items-baseline gap-2 truncate" title="${v.word || v.kana || ''}">
        <span class="text-[10px] font-mono text-neutral-400">${String(i + 1).padStart(2, '0')}</span>
        <span class="font-bold jp-font text-sm text-[#111111]">${v.word || v.kana || ''}</span>
        ${v.reading && v.reading !== v.word && !v.reading.startsWith(v.word) ? `<span class="text-[10px] font-mono text-neutral-400">(${v.reading.replace(/[（\(].*?[）\)]/g, '')})</span>` : ''}
        ${reqBadge}
      </div>
      <span class="font-mono text-[11px] text-neutral-600 truncate max-w-[200px]" title="${v.meaning || v.english || ''}">${v.meaning || v.english || ''}</span>
    </div>`;
  }).join('');
}

export function renderGrammarPreview(items) {
  const container = document.getElementById('previewGrammarContainer');
  if (!container) return;
  if (!items.length) {
    container.innerHTML = '<div class="text-xs text-neutral-400 py-2">Nessun punto grammaticale in coda.</div>';
    return;
  }
  const isAnyLocked = items.some(g => g.is_locked || (g.unreviewed_vocab_count || g.missing_vocab?.length || 0) > 0);
  const badgeTxt = isAnyLocked ? '🔒 Bloccata (REQ mancanti)' : '5 pronte (Sbloccate)';
  const bBadge = document.getElementById('branch_grammar_badge');
  const lBadge = document.getElementById('leaf_grammar_badge');
  if (bBadge) bBadge.innerHTML = `<span class="${isAnyLocked ? 'text-[#C23B22]' : 'text-[#264332]'} font-bold">${isAnyLocked ? '🔒 Bloccata' : '5 pronte'}</span>`;
  if (lBadge) lBadge.innerHTML = `<span class="${isAnyLocked ? 'text-[#C23B22]' : 'text-[#264332]'} font-bold">${badgeTxt}</span>`;

  const btnSync = document.getElementById('btnSyncGrammar');
  if (btnSync) {
    btnSync.disabled = isAnyLocked;
    btnSync.className = isAnyLocked ? 'px-4 py-1.5 bg-neutral-300 text-neutral-500 font-mono text-xs font-bold uppercase tracking-wider cursor-not-allowed opacity-60' : 'px-4 py-1.5 bg-[#C23B22] hover:bg-[#181A1B] text-white font-mono text-xs font-bold uppercase tracking-wider transition tap-press';
    btnSync.innerText = isAnyLocked ? '🔒 In attesa di vocaboli REQ (Bloccata)' : 'Sincronizza Gruppo (5) →';
  }

  container.innerHTML = items.map(g => {
    const isLocked = g.is_locked || (g.unreviewed_vocab_count || g.missing_vocab?.length || 0) > 0;
    const cBadge = g.cluster || g.mext_cluster ? `<span class="text-[9px] font-mono px-1 py-0.5 bg-[#EEF7F1] text-[#1E5233] border border-[#1E5233]/20 font-bold">${(g.cluster || g.mext_cluster).split(':')[0]}</span>` : '';
    const samples = (g.unreviewed_vocab_samples || g.missing_vocab || []).slice(0, 5).join(', ');
    const lockInfo = isLocked ? `
      <div class="mt-1 p-1.5 bg-[#FDF1EF] border border-[#C23B22]/20 text-[10px] font-mono flex items-center justify-between gap-1">
        <span class="text-[#C23B22] truncate" title="Mancano: ${samples}">🔒 <b>BLOCCATA:</b> mancano <b>${samples}</b></span>
        <button onclick="switchStudyBranch('vocab')" class="flex-shrink-0 text-[9px] px-1 py-0.5 bg-[#C23B22] text-white font-bold hover:bg-black uppercase tap-press active:scale-95 transition">Studia REQ →</button>
      </div>` : `
      <div class="mt-1 px-1.5 py-0.5 bg-[#EEF7F1] border border-[#264332]/20 text-[10px] font-mono text-[#264332] font-bold flex items-center justify-between">
        <span>🔓 <b>SBLOCCATA:</b> Tutti i vocaboli studiati</span>
        <span class="text-[9px] px-1 bg-[#264332] text-white uppercase font-mono">Pronta</span>
      </div>`;
    const sList = (g.sentences || []).slice(0, 2).map(s => `
      <div class="p-1.5 bg-[#FAF8F5] border border-black/5 text-xs">
        <div class="jp-font text-[#111111] font-medium">${s.clean_jp || s.plain_jp || ''}</div>
        <div class="text-[10px] font-mono text-neutral-500">${s.clean_en || ''}</div>
      </div>`).join('');
    const sBox = sList ? `<div class="mt-1.5 pt-1.5 border-t border-black/5 space-y-1"><div class="text-[10px] font-mono text-neutral-400 font-bold">FRASI BUNPRO:</div>${sList}</div>` : '';
    return `
    <div class="p-2.5 border border-black/10 bg-white space-y-1 animate-info-fade">
      <div class="flex items-center justify-between text-xs">
        <span class="font-bold jp-font text-sm text-[#111111]">${g.title}</span>
        <div class="flex items-center gap-1">${cBadge}<span class="text-[10px] font-mono px-1.5 py-0.5 bg-neutral-100 text-neutral-600">${g.level}</span></div>
      </div>
      <div class="text-[11px] text-neutral-600 italic font-mono">${g.meaning}</div>
      ${lockInfo}
      ${sBox}
    </div>`;
  }).join('');
}
