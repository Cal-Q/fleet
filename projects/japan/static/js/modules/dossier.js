// static/js/modules/dossier.js — UniTO Esse3 Career & Document Checklist
// Strictly <= 200 lines invariant.

export async function loadCareer() {
  try {
    const res = await fetch('/api/career');
    const data = await res.json();

    const gpaEl = document.getElementById('careerMextGpa');
    const cfuEl = document.getElementById('careerAreaCfu');
    const tableBody = document.getElementById('careerTableBody');
    if (gpaEl && data.summary) gpaEl.innerText = `${Number(data.summary.mext_gpa_attuale || 3.0).toFixed(2)} / 3.00`;
    if (cfuEl && data.summary) cfuEl.innerText = `${data.summary.cfu_area_superati || 8} CFU`;

    const allExams = [
      ...(data.attivita_superate || []),
      ...(data.attivita_in_corso_frequentate || [])
    ];

    if (tableBody && allExams.length) {
      tableBody.innerHTML = allExams.map(e => {
        const isSuperata = e.status === 'Superata';
        const isCertified = e.code?.startsWith('SHOWA');
        const statusBadge = isCertified
          ? '<span class="px-2 py-0.5 text-[10px] font-mono font-bold bg-[#FAF9F6] text-neutral-800 border border-black/20">ESTERNO (SHOWA)</span>'
          : (isSuperata
            ? '<span class="px-2 py-0.5 text-[10px] font-mono font-bold bg-[#EEF7F1] text-[#1E5233] border border-[#1E5233]/30">VERBALIZZATO</span>'
            : '<span class="px-2 py-0.5 text-[10px] font-mono font-bold bg-[#FDF1EF] text-[#E63920] border border-[#E63920]/30">IN CORSO</span>');

        return `
          <tr class="border-b border-black/5 hover:bg-black/[0.01] transition-colors text-xs font-mono">
            <td class="py-2.5 px-3 font-bold text-[#111111]">${e.code}</td>
            <td class="py-2.5 px-3 font-sans font-medium text-neutral-800">${e.name}</td>
            <td class="py-2.5 px-3 text-center font-bold">${e.cfu}</td>
            <td class="py-2.5 px-3 text-center font-bold text-[#111111]">${e.grade || '—'}</td>
            <td class="py-2.5 px-3 text-center text-neutral-500">${e.date || '—'}</td>
            <td class="py-2.5 px-3 text-right">${statusBadge}</td>
          </tr>
        `;
      }).join('');
    }
  } catch (err) {
    console.error('Error loading career:', err);
  }
}

export async function loadDossierStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    const sizeEl = document.getElementById('attachmentsSize');
    if (sizeEl) sizeEl.innerText = `${data.total_attachment_mb} / 10.0 MB`;

    const listEl = document.getElementById('dossierChecklist');
    if (!listEl) return;
    listEl.innerHTML = '';

    const statusBadges = {
      certified: '<span class="px-2 py-0.5 text-[10px] font-mono font-bold bg-[#EEF7F1] text-[#1E5233] border border-[#1E5233]/20">ACQUISITO</span>',
      in_progress: '<span class="px-2 py-0.5 text-[10px] font-mono font-bold bg-[#FDF1EF] text-[#E63920] border border-[#E63920]/20">IN STESURA</span>',
      pending_issuance: '<span class="px-2 py-0.5 text-[10px] font-mono font-bold bg-amber-50 text-amber-800 border border-amber-200">IN ATTESA RILASCIO</span>',
      to_collect: '<span class="px-2 py-0.5 text-[10px] font-mono font-bold bg-neutral-100 text-neutral-600 border border-neutral-200">DA RICHIEDERE</span>'
    };

    data.items.forEach(item => {
      const card = document.createElement('div');
      card.className = 'p-3 border border-black/10 bg-white flex flex-col justify-between gap-3 text-xs';
      card.innerHTML = `
        <div class="space-y-1">
          <div class="flex items-center justify-between font-mono text-[10px] text-neutral-400">
            <span>DOC #${item.id}</span>
            <span>${item.size_kb > 0 ? `${item.size_kb} KB` : 'In attesa file'}</span>
          </div>
          <h4 class="font-bold font-sans text-sm text-[#111111]">${item.name}</h4>
          <p class="text-[11px] text-neutral-600 font-mono leading-relaxed">${item.notes}</p>
        </div>
        <div class="flex items-center justify-between pt-2 border-t border-black/5 font-mono text-xs">
          <div>${statusBadges[item.status] || item.status}</div>
          <select onchange="window.updateDocStatus(${item.id}, this.value)" class="text-[10px] bg-neutral-50 border border-black/20 px-2 py-1 uppercase font-bold text-neutral-700 cursor-pointer">
            <option value="certified" ${item.status === 'certified' ? 'selected' : ''}>Acquisito</option>
            <option value="in_progress" ${item.status === 'in_progress' ? 'selected' : ''}>In corso</option>
            <option value="pending_issuance" ${item.status === 'pending_issuance' ? 'selected' : ''}>Attesa</option>
            <option value="to_collect" ${item.status === 'to_collect' ? 'selected' : ''}>Da richiedere</option>
          </select>
        </div>
      `;
      listEl.appendChild(card);
    });
  } catch (err) {
    console.error('Error loading dossier status:', err);
  }
}

export async function updateDocStatus(id, newStatus) {
  try {
    await fetch('/api/status/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item_id: id, status: newStatus })
    });
    loadDossierStatus();
  } catch (err) {
    console.error('Error updating status:', err);
  }
}

export function switchDossierBranch(branch) {
  const isCareer = branch === 'career';
  const leafCareer = document.getElementById('leaf_dossier_career');
  const leafChecklist = document.getElementById('leaf_dossier_checklist');
  const btnCareer = document.getElementById('branch_btn_dossier_career');
  const btnChecklist = document.getElementById('branch_btn_dossier_checklist');
  if (leafCareer) leafCareer.classList.toggle('hidden', !isCareer);
  if (leafChecklist) leafChecklist.classList.toggle('hidden', isCareer);
  if (btnCareer) {
    btnCareer.classList.toggle('bg-white', isCareer);
    btnCareer.classList.toggle('opacity-70', !isCareer);
  }
  if (btnChecklist) {
    btnChecklist.classList.toggle('bg-white', !isCareer);
    btnChecklist.classList.toggle('opacity-70', isCareer);
  }
}
