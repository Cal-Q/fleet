// static/js/modules/research.js — Academic Research Dossiers Browser
// Strictly <= 200 lines invariant.

export async function loadResearchDossiers() {
  try {
    const res = await fetch('/api/research/dossiers');
    const items = await res.json();
    const listEl = document.getElementById('researchDossiersList');
    if (!listEl) return;

    if (!Array.isArray(items) || !items.length) {
      listEl.innerHTML = '<div class="text-xs font-mono text-neutral-400 py-3 text-center">Nessun dossier archiviato.</div>';
      return;
    }

    listEl.innerHTML = items.map(d => `
      <div class="p-4 border border-black/10 bg-white hover:border-black transition flex flex-col justify-between gap-3 text-xs">
        <div class="space-y-1">
          <div class="flex items-center justify-between font-mono text-[10px] text-neutral-400">
            <span>${d.modified?.split(' ')[0] || '2026'}</span>
            <span>${d.size_str || (d.size_bytes / 1024).toFixed(1) + ' KB'}</span>
          </div>
          <h4 class="font-bold font-sans text-sm text-[#111111] leading-snug">${d.title || d.filename}</h4>
          <p class="text-[11px] text-neutral-600 font-mono truncate" title="${d.filename}">${d.filename}</p>
        </div>
        <div class="pt-2 border-t border-black/5 flex items-center justify-between">
          <span class="text-[10px] font-mono text-neutral-500">Documento Verificato</span>
          <button onclick="window.previewDossier('${d.filename}')" class="px-2.5 py-1 border border-black text-[10px] font-mono font-bold uppercase hover:bg-black hover:text-white transition tap-press">
            Leggi Dossier →
          </button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Error loading research dossiers:', err);
  }
}

export async function previewDossier(filename) {
  const viewer = document.getElementById('dossierViewerBox');
  const titleEl = document.getElementById('dossierViewerTitle');
  const bodyEl = document.getElementById('dossierViewerContent');
  if (!viewer || !titleEl || !bodyEl) return;

  try {
    const res = await fetch(`/api/research/dossier/${encodeURIComponent(filename)}`);
    const data = await res.json();
    titleEl.innerText = filename;
    bodyEl.innerText = data.markdown || 'Contenuto non disponibile.';
    viewer.classList.remove('hidden');
  } catch (err) {
    console.error('Error previewing dossier:', err);
  }
}

