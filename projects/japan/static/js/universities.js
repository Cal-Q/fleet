/**
 * universities.js — Placement Preference Form & Universities Catalog
 * Highlights the 3 recommended placement choices and provides full Course Guide search.
 * Strictly <= 200 lines invariant. Sinoira Gang hairline broadsheet.
 */

let allUnis = [];
let onlySelectedFilter = false;

async function loadUniversities() {
  try {
    const res = await fetch('/api/universities');
    if (!res.ok) return;
    allUnis = await res.json();
    renderPlacementPreferences();
    renderUnis(allUnis);
  } catch (err) {
    console.error('Error loading universities:', err);
  }
}

function renderPlacementPreferences() {
  const container = document.getElementById('placementPreferencesCards');
  if (!container) return;

  const prefUnis = allUnis.filter(u => u.preference_rank).sort((a, b) => a.preference_rank - b.preference_rank);
  if (prefUnis.length === 0) return;

  container.innerHTML = '';
  prefUnis.forEach(u => {
    const isReserve = u.is_reserve;
    const card = document.createElement('div');
    card.className = `p-4 border flex flex-col justify-between space-y-3 transition ${
      isReserve 
        ? 'bg-[#FAF9F6] border-black/10' 
        : 'bg-white border-black/30 hover:border-black'
    }`;

    const rankBadge = isReserve
      ? '<span class="px-2 py-0.5 text-[10px] bg-[#FAF9F6] text-neutral-600 border border-black/20 font-bold font-mono uppercase">📌 Riserva</span>'
      : `<span class="px-2 py-0.5 text-[10px] bg-[#FDF1EF] text-[#E63920] border border-[#E63920]/30 font-bold font-mono uppercase">${u.preference_label}</span>`;

    card.innerHTML = `
      <div class="space-y-2">
        <div class="flex items-center justify-between border-b border-black/10 pb-2">
          ${rankBadge}
          <span class="font-mono text-xs font-semibold text-neutral-500">Codice: <strong class="text-[#111111]">${u.id}</strong></span>
        </div>
        <div>
          <h3 class="font-bold text-sm text-[#111111] font-sans">${u.name_en}</h3>
          <div class="jp-font text-xs text-neutral-500">${u.name_ja}</div>
          <p class="text-xs text-neutral-600 mt-0.5 font-mono">📍 ${u.location_en}</p>
        </div>
        <div class="text-[11px] text-neutral-700 bg-[#FAF9F6] p-2.5 border border-black/10 space-y-1">
          <div class="font-bold text-[#111111] font-mono">Centro / Struttura:</div>
          <div>${u.faculty_center || u.focus}</div>
          <div class="font-bold text-[#111111] pt-1 font-mono">Studio Plan:</div>
          <p class="text-neutral-600 leading-relaxed">${u.sociological_rationale || ''}</p>
        </div>
      </div>
      <div class="pt-2 border-t border-black/10 flex items-center justify-between text-xs font-mono">
        <span class="px-2 py-0.5 bg-[#FAF9F6] text-[#111111] font-medium border border-black/10">${u.course_types_str}</span>
        <span class="text-neutral-500">Guida: p. ${u.guide_page}</span>
      </div>
    `;
    container.appendChild(card);
  });
}

function renderUnis(list) {
  const grid = document.getElementById('unisGrid');
  if (!grid) return;
  grid.innerHTML = '';

  list.forEach(u => {
    const isSelected = !!u.preference_rank;
    const card = document.createElement('div');
    card.className = `p-4 border flex flex-col justify-between space-y-3 transition ${
      isSelected 
        ? 'bg-white border-black hover:border-[#E63920]' 
        : 'bg-white border-black/10 hover:border-black'
    }`;

    const badgeTop = isSelected
      ? `<span class="px-2 py-0.5 bg-[#FDF1EF] text-[#E63920] font-bold text-[10px] border border-[#E63920]/30 font-mono">${u.preference_label}</span>`
      : `<span class="px-1.5 py-0.5 bg-[#FAF9F6] text-neutral-600 border border-black/10 text-[10px] font-mono">${u.category.split(' ')[0]}</span>`;

    card.innerHTML = `
      <div>
        <div class="flex items-center justify-between text-xs text-neutral-500 border-b border-black/10 pb-1.5 mb-2 font-mono">
          <span class="font-semibold ${isSelected ? 'text-[#E63920] font-bold' : 'text-neutral-600'}">No. ${u.id}</span>
          ${badgeTop}
        </div>
        <h3 class="font-bold text-[#111111] text-sm">${u.name_en}</h3>
        <div class="jp-font text-xs text-neutral-500">${u.name_ja}</div>
        <p class="text-xs text-neutral-600 mt-1 font-mono">📍 ${u.location_en} (${u.region})</p>
        ${isSelected ? `<p class="text-[11px] text-[#E63920] mt-2 font-mono bg-[#FDF1EF] p-1.5 border border-[#E63920]/20">✅ Selezionata nel Preference Form</p>` : ''}
      </div>
      <div class="pt-2 border-t border-black/10 flex items-center justify-between text-xs font-mono">
        <span class="px-2 py-0.5 bg-[#FAF9F6] text-neutral-700 font-medium border border-black/10">${u.course_types_str}</span>
        <span class="text-neutral-500">Guida: p. ${u.guide_page}</span>
      </div>
    `;
    grid.appendChild(card);
  });
}

function toggleSelectedFilter() {
  onlySelectedFilter = !onlySelectedFilter;
  const btn = document.getElementById('uniBtnOnlySelected');
  if (btn) {
    if (onlySelectedFilter) {
      btn.className = "px-2.5 py-1.5 border bg-[#111111] text-white border-black text-xs font-mono font-medium transition tap-press";
    } else {
      btn.className = "px-2.5 py-1.5 border bg-[#FAF9F6] text-[#111111] border-black/20 hover:border-black text-xs font-mono font-medium transition tap-press";
    }
  }
  filterUnis();
}

function filterUnis() {
  const q = (document.getElementById('uniSearch') ? document.getElementById('uniSearch').value : '').toLowerCase();
  const t = document.getElementById('uniTypeFilter') ? document.getElementById('uniTypeFilter').value : '';

  const filtered = allUnis.filter(u => {
    if (onlySelectedFilter && !u.preference_rank) return false;
    const matchesQ = !q || u.name_en.toLowerCase().includes(q) || u.name_ja.includes(q) || u.location_en.toLowerCase().includes(q) || String(u.id) === q;
    const matchesT = !t || u.course_types.includes(t);
    return matchesQ && matchesT;
  });
  renderUnis(filtered);
}

function switchUnisBranch(branch) {
  const isPref = branch === 'pref';
  const leafPref = document.getElementById('leaf_unis_pref');
  const leafCatalog = document.getElementById('leaf_unis_catalog');
  const btnPref = document.getElementById('branch_btn_unis_pref');
  const btnCatalog = document.getElementById('branch_btn_unis_catalog');
  if (leafPref) leafPref.classList.toggle('hidden', !isPref);
  if (leafCatalog) leafCatalog.classList.toggle('hidden', isPref);
  if (btnPref) {
    btnPref.classList.toggle('bg-white', isPref);
    btnPref.classList.toggle('opacity-70', !isPref);
  }
  if (btnCatalog) {
    btnCatalog.classList.toggle('bg-white', !isPref);
    btnCatalog.classList.toggle('opacity-70', isPref);
  }
}

window.loadUniversities = loadUniversities;
window.toggleSelectedFilter = toggleSelectedFilter;
window.filterUnis = filterUnis;
window.switchUnisBranch = switchUnisBranch;

