// static/js/modules/routine_curriculum.js — Live Granular Prescription & Dynamic Routine Sync
// Strictly <= 200 lines invariant.

export async function syncCurriculumPlan() {
  try {
    const res = await fetch('/api/curriculum/daily-plan');
    if (!res.ok) return;
    const data = await res.json();
    if (!data.success || !data.plan) return;

    const plan = data.plan;
    renderDynamicSlotLabels(plan);
    renderPrescriptionDrawer(plan);
    loadMilestonesPreview();
  } catch (err) {
    console.warn('Could not sync curriculum plan:', err);
  }
}

function renderDynamicSlotLabels(plan) {
  const tasks = plan.tasks || [];
  tasks.forEach(t => {
    const card = document.getElementById(`slotCard${t.slot}`);
    if (!card) return;
    const descEl = card.querySelector('div.text-\\[10px\\]');
    const titleEl = card.querySelector('div.text-\\[11px\\]');

    if (t.slot === 1 && descEl) {
      descEl.innerText = `${t.live_status || '5.052 mature'} (Anki)`;
    } else if (t.slot === 2) {
      if (titleEl) titleEl.innerText = `13:00 • Sprint N4 (${t.est_minutes}m)`;
      if (descEl && t.items) descEl.innerText = `${t.items.length} punti odierni (#${t.items[0]?.id || ''}...)`;
    } else if (t.slot === 3) {
      if (titleEl) titleEl.innerText = `18:00 • Frasi & Keigo (${t.est_minutes}m)`;
      if (descEl) descEl.innerText = '12 verbi & sintassi N4';
    } else if (t.slot === 4) {
      if (titleEl) titleEl.innerText = `21:00 • Drill Part A (${t.est_minutes}m)`;
      if (descEl) descEl.innerText = '10-12 quesiti mirati';
    }
  });

  const progText = document.getElementById('routineProgressText');
  if (progText && plan.total_estimated_hours) {
    const todayStr = new Date().toISOString().split('T')[0];
    const state = JSON.parse(localStorage.getItem('mext_routine_' + todayStr) || '{}');
    const doneCount = ['slot1', 'slot2', 'slot3', 'slot4'].filter(k => state[k]).length;
    const pct = Math.round((doneCount / 4) * 100);
    progText.innerText = `${doneCount}/4 Completati (${pct}%) • ${plan.total_estimated_hours}h nette oggi`;
  }
}

function renderPrescriptionDrawer(plan) {
  const container = document.getElementById('dailyPrescriptionDetail');
  if (!container) return;

  const slot2 = plan.tasks.find(t => t.slot === 2);
  const items = slot2?.items || [];
  const p1 = plan.trajectory?.phases?.phase1;

  container.innerHTML = `
    <div class="mt-2.5 pt-2.5 border-t border-black/10 space-y-2">
      <div class="flex items-center justify-between">
        <span class="font-bold text-[#181A1B] uppercase text-[10px]">Prescrizione Operativa di Oggi (${plan.date})</span>
        <span class="px-1.5 py-0.5 bg-[#264332] text-white text-[10px] font-bold">${plan.total_estimated_minutes} min totali (${plan.total_estimated_hours}h)</span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px]">
        <div class="p-2 border border-[#264332]/30 bg-white space-y-1">
          <strong class="text-[#264332] flex items-center justify-between">
            <span>📚 Grammatica Bunpro di Oggi (45 min):</span>
            <span class="text-[10px] font-normal text-neutral-500">N4: ${p1?.grammar_remaining || 47} rimanenti (${p1?.end_date || '24/09'})</span>
          </strong>
          <ul class="space-y-1 mt-1 text-[11px]">
            ${items.map(it => `
              <li class="flex items-start justify-between gap-1 border-b border-black/5 pb-0.5">
                <div>
                  <span class="font-bold text-[#181A1B] jp-font text-xs">${it.title}</span>
                  <span class="text-neutral-500 text-[10px] ml-1">(${it.meaning})</span>
                </div>
                <a href="${it.url}" target="_blank" class="text-[10px] text-[#264332] font-mono hover:underline whitespace-nowrap">Apri ↗</a>
              </li>
            `).join('')}
          </ul>
        </div>

        <div class="p-2 border border-black/10 bg-white space-y-1.5">
          <strong class="text-[#181A1B]">⚡ Altri 3 Task di Oggi:</strong>
          <div class="text-[10px] text-neutral-700 space-y-1">
            <div class="p-1 bg-[#FAF8F5] border border-black/5">
              <strong class="text-[#181A1B]">Slot 1 (40m):</strong> Anki SRS mature (${plan.tasks[0]?.live_status || '5.052'}).
            </div>
            <div class="p-1 bg-[#FAF8F5] border border-black/5">
              <strong class="text-[#1E2C3A]">Slot 3 (25m):</strong> Frasi per i 4 punti odierni + 12 verbi Keigo (carte). No intervista complessa.
            </div>
            <div class="p-1 bg-[#FAF8F5] border border-black/5">
              <strong class="text-[#C23B22]">Slot 4 (15m):</strong> Drill 10-12 quesiti mirati di Parte A con annotazione dubbi.
            </div>
          </div>
        </div>
      </div>

      <div id="masterTimelineSection" class="pt-2 border-t border-black/5">
        <button onclick="window.toggleMasterTimeline()" class="text-[10px] font-mono font-bold text-neutral-600 hover:text-black transition flex items-center gap-1 tap-press active:scale-95">
          <span>📅</span> <span>Mostra Tappe Miliari Traiettoria 161 Giorni ↓</span>
        </button>
        <div id="masterTimelineDrawer" class="hidden mt-2 p-2 bg-white border border-black/10 text-[10px] font-mono space-y-1"></div>
      </div>
    </div>
  `;
}

async function loadMilestonesPreview() {
  try {
    const res = await fetch('/api/curriculum/master');
    if (!res.ok) return;
    const data = await res.json();
    const days = data.days || [];
    const milestones = days.filter(d => d.milestone);
    const drawer = document.getElementById('masterTimelineDrawer');
    if (!drawer) return;

    drawer.innerHTML = `
      <div class="font-bold text-[#181A1B] mb-1">🎯 9 Tappe Miliari Chiave (161 Giorni Deterministici):</div>
      <div class="space-y-1">
        ${milestones.map(m => `
          <div class="flex items-center justify-between gap-2 p-1 border-b border-black/5">
            <span class="font-bold text-[#264332]">Giorno ${m.day_number} (${m.date})</span>
            <span class="text-neutral-700 truncate">${m.milestone}</span>
          </div>
        `).join('')}
      </div>
    `;
  } catch (err) {
    console.warn('Could not load milestones preview:', err);
  }
}

window.toggleMasterTimeline = function() {
  const drawer = document.getElementById('masterTimelineDrawer');
  if (drawer) drawer.classList.toggle('hidden');
};
