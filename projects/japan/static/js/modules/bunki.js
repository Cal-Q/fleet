// static/js/modules/bunki.js — Bunki Engine Status & Leech Manager
// Strictly <= 200 lines invariant.

export async function loadBunkiProfile() {
  try {
    const res = await fetch('/api/bunki/profile');
    const data = await res.json();

    const mEl = document.getElementById('bunkiMatureCount');
    const tEl = document.getElementById('bunkiTotalReviews');
    const vEl = document.getElementById('bunkiVocabKnown');
    const kEl = document.getElementById('bunkiKanjiWriting');
    if (mEl) mEl.innerText = data.mature_cards?.toLocaleString() || '5,052';
    if (tEl) tEl.innerText = data.total_reviews?.toLocaleString() || '213,839';
    if (vEl) vEl.innerText = data.core_metrics?.vocab_known?.toLocaleString() || '3,400';
    if (kEl) kEl.innerText = data.core_metrics?.kanji_writing?.toLocaleString() || '913';

    const decksList = document.getElementById('bunkiDecksList');
    if (decksList && data.active_decks) {
      decksList.innerHTML = Object.entries(data.active_decks).map(([name, d]) => `
        <div class="p-3 border border-black/10 bg-white space-y-1 text-xs">
          <div class="font-mono font-bold text-[#111111] truncate" title="${name}">${name}</div>
          <div class="flex items-center justify-between text-[11px] font-mono text-neutral-500 pt-1 border-t border-black/5">
            <span>Tot: <b>${d.total}</b></span>
            <span>Rev: <b class="text-[#1E5233]">${d.review}</b></span>
            <span>Lrn: <b class="text-amber-600">${d.learning}</b></span>
            <span>New: <b class="text-[#E63920]">${d.new}</b></span>
          </div>
        </div>
      `).join('');
    }

    loadLeeches();
    syncSlot1UI();
  } catch (err) {
    console.error('Error loading bunki profile:', err);
  }
}

export async function loadLeeches() {
  try {
    const res = await fetch('/api/leeches');
    const data = await res.json();
    const listEl = document.getElementById('leechesList');
    if (!listEl) return;

    if (!data.items?.length) {
      listEl.innerHTML = '<div class="text-xs font-mono text-neutral-400 py-3 text-center">Nessun leech sospeso al momento. Il database SRS è pulito.</div>';
      return;
    }

    listEl.innerHTML = data.items.map(item => `
      <div class="p-2.5 border-b border-black/10 flex items-center justify-between gap-4 text-xs">
        <div>
          <div class="font-bold jp-font text-base text-[#111111]">${item.word}</div>
          <div class="font-mono text-[10px] text-neutral-500">${item.deck_name} • Lapsi: ${item.lapses}</div>
        </div>
        <div class="flex items-center gap-1.5 font-mono text-[10px]">
          <button onclick="window.reviewLeechAction(${item.card_id}, 'rehabilitate')" class="px-2 py-0.5 border border-black hover:bg-black hover:text-white uppercase font-bold transition">
            Riabilita
          </button>
          <button onclick="window.reviewLeechAction(${item.card_id}, 'retire')" class="px-2 py-0.5 border border-neutral-300 text-neutral-400 hover:text-neutral-700 uppercase font-bold transition">
            Archivia
          </button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Error loading leeches:', err);
  }
}

export async function reviewLeechAction(cardId, action) {
  try {
    const res = await fetch('/api/leeches/review', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ card_id: cardId, action })
    });
    const data = await res.json();
    if (data.status === 'ok') {
      loadLeeches();
    }
  } catch (err) {
    console.error('Error reviewing leech:', err);
  }
}

function renderSlot1UI(dueCount, revDone, isDone) {
  const badge = document.getElementById('slot1StatusBadge');
  const btn = document.getElementById('btnSlot1VerifyAction');
  if (badge) {
    badge.className = isDone 
      ? 'text-[10px] font-mono font-bold px-2 py-1 border border-[#264332]/30 bg-[#EEF7F1] text-[#264332] uppercase'
      : 'text-[10px] font-mono font-bold px-2 py-1 border border-[#C23B22]/30 bg-[#FDF1EF] text-[#C23B22] uppercase';
    badge.innerText = isDone ? '✅ COMPLETATO (1/4h)' : `DA COMPLETARE (${dueCount} IN SCADENZA)`;
  }
  if (btn) {
    btn.disabled = false;
    btn.className = isDone
      ? 'w-full py-2.5 px-4 bg-[#EEF7F1] border border-[#264332]/40 text-[#264332] font-mono text-xs font-bold uppercase tracking-wider cursor-default flex items-center justify-center gap-2'
      : 'w-full py-2.5 px-4 bg-[#181A1B] hover:bg-[#264332] text-white font-mono text-xs font-bold uppercase tracking-wider transition tap-press flex items-center justify-center gap-2';
    btn.innerHTML = isDone
      ? '<span>✅ Ripasso SRS Convalidato (0 Arretrati in Travel)</span>'
      : `<span>🔄 Verifica Sincronizzazione AnkiWeb (${dueCount} in scadenza)</span>`;
  }
}

export async function syncSlot1UI() {
  const todayStr = new Date().toISOString().split('T')[0];
  const storageKey = 'mext_routine_' + todayStr;
  const state = JSON.parse(localStorage.getItem(storageKey) || '{}');

  try {
    const res = await fetch('/api/bunki/srs_status');
    const data = await res.json();
    const dueCount = data.due_total || 0;
    const isDone = !!data.verified && dueCount === 0;

    if (isDone) {
      if (!state['slot1'] && typeof window.markRoutineSlotDone === 'function') window.markRoutineSlotDone('slot1');
    } else {
      if (state['slot1'] && typeof window.unmarkRoutineSlot === 'function') window.unmarkRoutineSlot('slot1');
    }
    renderSlot1UI(dueCount, data.today_reviews || 0, isDone);
  } catch (err) {
    renderSlot1UI(0, 0, !!state['slot1']);
  }
}

export async function verifySlot1WithAnkiWeb() {
  const btn = document.getElementById('btnSlot1VerifyAction');
  const feedback = document.getElementById('slot1VerifyFeedback');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="animate-spin mr-1">⏳</span> <span>Connessione Relay & Query Revlog AnkiWeb...</span>';
  }
  if (feedback) feedback.classList.add('hidden');

  try {
    const res = await fetch('/api/bunki/verify_srs', { method: 'POST' });
    const data = await res.json();
    const dueCount = data.due_total || 0;
    const revDone = data.today_reviews || 0;
    const sub = data.travel_stats?.subdecks || {};
    const subSum = Object.entries(sub).filter(([_, s]) => s.due > 0).map(([k, s]) => `${s.due} ${k}`).join(', ');
    const isDone = !!data.verified && dueCount === 0 && revDone > 0;

    if (isDone) {
      if (typeof window.markRoutineSlotDone === 'function') window.markRoutineSlotDone('slot1');
      if (feedback) {
        feedback.className = 'p-2 bg-[#EEF7F1] border border-[#264332]/30 text-xs font-mono text-[#264332] block';
        feedback.innerHTML = `<b>✅ Lavoro Verificato:</b> Mazzi Travel completati (<b>${revDone}</b> ripassi odierni, <b>0</b> rimasti). Slot 1 registrato!`;
      }
    } else {
      if (typeof window.unmarkRoutineSlot === 'function') window.unmarkRoutineSlot('slot1');
      if (feedback) {
        feedback.className = 'p-2 bg-[#FDF1EF] border border-[#C23B22]/30 text-xs font-mono text-[#C23B22] block';
        feedback.innerHTML = dueCount > 0
          ? `<b>⚠️ SRS Travel Incompleto:</b> <b>${revDone}</b> ripassi svolti oggi, ma rimangono <b>${dueCount}</b> carte in scadenza (${subSum || 'in coda'}). Azzerale su Anki, sincronizza e riprova.`
          : `<b>⚠️ 0 Ripassi Rilevati:</b> Nessuna recensione registrata oggi nei mazzi Travel. Ripassa su Anki, premi <b>Sincronizza</b> e riprova.`;
      }
    }
    renderSlot1UI(dueCount, revDone, isDone);
  } catch (err) {
    if (btn) btn.disabled = false;
    if (feedback) {
      feedback.className = 'p-2 bg-[#FDF1EF] border border-[#C23B22]/30 text-xs font-mono text-[#C23B22] block';
      feedback.innerText = 'Errore verifica relay: ' + err.message;
    }
  }
}

