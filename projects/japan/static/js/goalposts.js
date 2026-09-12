/**
 * goalposts.js — Live Sunday Goalposts & Progress Telemetry
 * Synchronizes real-time Bunpro, Anki, and Esse3 metrics with 25-week schedule.
 * Strictly <= 200 lines invariant. Zero Modals.
 */

let goalpostsData = null;
let goalpostsFilter = 'all';

async function loadGoalposts() {
  try {
    const res = await fetch('/api/goalposts');
    if (!res.ok) return;
    goalpostsData = await res.json();

    const current = goalpostsData.current_review;
    const schedule = goalpostsData.schedule || {};
    const weeks = schedule.weeks || [];

    if (current) {
      const titleEl = document.getElementById('gpCurrentTitle');
      if (titleEl) titleEl.innerText = `Settimana W${String(current.week).padStart(2, '0')}: ${current.phase || ''}`;

      const dateEl = document.getElementById('gpActiveDate');
      if (dateEl && current.goalpost_date) {
        const d = new Date(current.goalpost_date + 'T00:00:00');
        const options = { day: '2-digit', month: 'long', year: 'numeric' };
        dateEl.innerText = d.toLocaleDateString('it-IT', options);
      }

      const m = current.live_metrics || {};
      const stdEl = document.getElementById('gpN4Studied');
      const remEl = document.getElementById('gpN4Remaining');
      if (stdEl && m.n4_studied) stdEl.innerText = `${m.n4_studied} lezioni`;
      if (remEl && m.n4_remaining !== undefined) remEl.innerText = `${m.n4_remaining} residue a Settembre`;

      const n3StdEl = document.getElementById('gpN3Studied');
      const n3PctEl = document.getElementById('gpN3Pct');
      if (n3StdEl && m.n3_studied) n3StdEl.innerText = `${m.n3_studied} lezioni`;
      if (n3PctEl && m.n3_studied) {
        const [n3Std, n3Tot] = m.n3_studied.split('/').map(Number);
        n3PctEl.innerText = `${((n3Std / (n3Tot || 1)) * 100).toFixed(1)}% completato`;
      }

      const gpaEl = document.getElementById('gpGpaVal');
      if (gpaEl && m.mext_gpa !== undefined) {
        gpaEl.innerText = `${Number(m.mext_gpa).toFixed(2)} / 3.00`;
      }

      const cfuEl = document.getElementById('gpCfuVal');
      if (cfuEl && m.cfu_area_certified !== undefined) {
        cfuEl.innerText = `${m.cfu_area_certified} CFU Area (30L)`;
      }

      const curWeekNum = current.week !== undefined ? current.week : 0;
      const nextWeek = weeks.find(w => w.week === curWeekNum + 1) || weeks.find(w => w.week > curWeekNum);
      if (nextWeek) {
        const titleTarget = document.getElementById('gpNextTargetTitle');
        const detailsTarget = document.getElementById('gpNextTargetDetails');
        if (titleTarget) titleTarget.innerText = `Target per la Prossima Domenica (W${String(nextWeek.week).padStart(2, '0')} - ${nextWeek.date}):`;
        if (detailsTarget) {
          detailsTarget.innerHTML = `• <strong>Grammatica Bunpro</strong>: ${nextWeek.target_grammar}<br>• <strong>Kanji & Vocaboli</strong>: ${nextWeek.target_kanji} • ${nextWeek.target_vocab}<br>• <strong>Milestone Amministrativa</strong>: ${nextWeek.milestone_admin}`;
        }
      }
    }
    renderGoalpostsTable();
  } catch (err) {
    console.error('Error loading goalposts:', err);
  }
}

function filterGoalposts(type) {
  goalpostsFilter = type;
  const btnAll = document.getElementById('gpFilterAll');
  const btnActive = document.getElementById('gpFilterActive');
  if (type === 'all') {
    if (btnAll) btnAll.className = "px-2.5 py-1 border bg-[#111111] text-white border-black transition tap-press";
    if (btnActive) btnActive.className = "px-2.5 py-1 border bg-[#FAF9F6] text-[#111111] border-black/20 hover:border-black transition tap-press";
  } else {
    if (btnAll) btnAll.className = "px-2.5 py-1 border bg-[#FAF9F6] text-[#111111] border-black/20 hover:border-black transition tap-press";
    if (btnActive) btnActive.className = "px-2.5 py-1 border bg-[#111111] text-white border-black transition tap-press";
  }
  renderGoalpostsTable();
}

function renderGoalpostsTable() {
  if (!goalpostsData || !goalpostsData.schedule) return;
  const tbody = document.getElementById('goalpostsTableBody');
  if (!tbody) return;

  const weeks = goalpostsData.schedule.weeks || [];
  const curWeekNum = goalpostsData.current_review ? goalpostsData.current_review.week : 0;
  const displayWeeks = goalpostsFilter === 'active' ? weeks.filter(w => w.week >= curWeekNum) : weeks;

  tbody.innerHTML = '';
  displayWeeks.forEach(w => {
    const isCurrent = w.week === curWeekNum;
    const tr = document.createElement('tr');
    tr.className = `transition ${isCurrent ? 'bg-[#FAF9F6] font-bold border-l-2 border-l-[#E63920]' : 'hover:bg-[#FAF9F6]'}`;

    const statusBadge = {
      'completed': '<span class="px-2 py-0.5 text-[10px] bg-[#FAF9F6] text-[#1E5233] border border-[#1E5233]/30 font-mono">✅ Completato</span>',
      'active': '<span class="px-2 py-0.5 text-[10px] bg-[#FDF1EF] text-[#E63920] border border-[#E63920]/30 font-bold font-mono">🎯 In Corso</span>',
      'pending': '<span class="px-2 py-0.5 text-[10px] bg-[#FAF9F6] text-neutral-500 border border-black/10 font-mono">⏳ Pianificato</span>'
    }[w.status] || `<span class="px-2 py-0.5 text-[10px] bg-[#FAF9F6] text-neutral-500 border border-black/10 font-mono">${w.status}</span>`;

    tr.innerHTML = `
      <td class="p-2.5 font-mono text-[11px] text-neutral-500">W${String(w.week).padStart(2, '0')}</td>
      <td class="p-2.5 font-mono text-[11px] text-[#111111] whitespace-nowrap">${w.date}</td>
      <td class="p-2.5 text-[#111111]">${w.phase}</td>
      <td class="p-2.5 text-neutral-600 font-mono text-[11px]">${w.target_grammar}</td>
      <td class="p-2.5 text-neutral-600 font-mono text-[11px]">${w.target_kanji} • ${w.target_vocab}</td>
      <td class="p-2.5 text-neutral-600 text-xs">${w.milestone_admin}</td>
      <td class="p-2.5 text-center whitespace-nowrap">${statusBadge}</td>
    `;
    tbody.appendChild(tr);
  });
}

function copySundayAuditReport() {
  if (!goalpostsData || !goalpostsData.current_review) return;
  const rev = goalpostsData.current_review;
  const m = rev.live_metrics || {};
  const t = rev.targets || {};

  const reportText = `[MEXT 2027] AUDIT DOMENICALE — Settimana W${String(rev.week).padStart(2, '0')} (${rev.goalpost_date})\nFase: ${rev.phase}\n--------------------------------------------------\n- Grammatica Bunpro: N4 ${m.n4_studied || '—'} (${m.n4_remaining || 0} residue), N3 ${m.n3_studied || '—'} [Target: ${t.grammar || '—'}]\n- Kanji KLC: Target ${t.kanji || '—'}\n- Vocaboli Anki: Target ${t.vocab || '—'}\n- Carriera UniTO: Esse3 GPA ${Number(m.mext_gpa || 3.0).toFixed(2)}/3.00 (${m.cfu_area_certified || 8} CFU Area)\n- Milestone Amministrativa: ${t.admin || '—'}\n--------------------------------------------------\nStato Audit: ${rev.status === 'completed' ? 'Completato al 100%' : 'In Corso'}`;

  navigator.clipboard.writeText(reportText).then(() => {
    alert('Resoconto audit copiato negli appunti!');
  });
}

function switchStrategyBranch(branch) {
  const isRoadmap = branch === 'roadmap';
  const leafRoadmap = document.getElementById('leaf_strategy_roadmap');
  const leafAudit = document.getElementById('leaf_strategy_audit');
  const btnRoadmap = document.getElementById('branch_btn_strategy_roadmap');
  const btnAudit = document.getElementById('branch_btn_strategy_audit');
  if (leafRoadmap) leafRoadmap.classList.toggle('hidden', !isRoadmap);
  if (leafAudit) leafAudit.classList.toggle('hidden', isRoadmap);
  if (btnRoadmap) {
    btnRoadmap.classList.toggle('bg-white', isRoadmap);
    btnRoadmap.classList.toggle('opacity-70', !isRoadmap);
  }
  if (btnAudit) {
    btnAudit.classList.toggle('bg-white', !isRoadmap);
    btnAudit.classList.toggle('opacity-70', isRoadmap);
  }
}

window.loadGoalposts = loadGoalposts;
window.filterGoalposts = filterGoalposts;
window.copySundayAuditReport = copySundayAuditReport;
window.switchStrategyBranch = switchStrategyBranch;

