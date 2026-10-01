// static/js/modules/srs_player_render.js — SRS Player Card & Button Rendering
// Strictly <= 200 lines invariant.

export function renderLoading(container) {
  if (!container) return;
  container.innerHTML = `
    <div class="h-full flex items-center justify-center p-8 text-neutral-400 font-mono text-xs">
      <span class="animate-spin mr-2">⏳</span> Caricamento carte Anki...
    </div>
  `;
}

export function renderEmpty(container, message) {
  if (!container) return;
  container.innerHTML = `
    <div class="h-full flex flex-col items-center justify-center p-8 text-neutral-500 font-mono text-xs text-center space-y-2">
      <span>${message || 'Nessuna carta disponibile.'}</span>
    </div>
  `;
}

export function renderCardView(container, card, isFlipped, counts, currentNum, total) {
  if (!container || !card) return;
  const ivls = card.intervals || { again: '<1m', hard: '10m', good: '1g', easy: '4g' };

  container.innerHTML = `
    <div class="h-full flex flex-col justify-between max-w-2xl mx-auto w-full p-2 sm:p-4 select-none">
      <!-- Top Anki Header Bar -->
      <div class="flex-shrink-0 flex items-center justify-between pb-2 border-b border-black/10 font-mono text-xs">
        <div class="flex items-center gap-3">
          <span class="px-2 py-0.5 bg-[#1E2C3A]/10 text-[#1E2C3A] font-bold border border-[#1E2C3A]/20" title="Nuove">${counts.new}</span>
          <span class="px-2 py-0.5 bg-[#C23B22]/10 text-[#C23B22] font-bold border border-[#C23B22]/20" title="Apprendimento">${counts.learning}</span>
          <span class="px-2 py-0.5 bg-[#264332]/10 text-[#264332] font-bold border border-[#264332]/20" title="Ripassi">${counts.review}</span>
        </div>
        <div class="flex items-center gap-2 text-neutral-500 text-[11px]">
          <span class="truncate max-w-[140px] sm:max-w-[200px]" title="${card.deck_name}">${card.deck_name}</span>
          <span class="font-bold text-black font-mono">(${currentNum}/${total})</span>
        </div>
      </div>

      <!-- Center Card Stage -->
      <div 
        id="srsCardBody"
        onclick="window.srsFlipCard()" 
        class="flex-grow my-3 bg-white border border-black/15 shadow-sm p-4 sm:p-8 flex flex-col justify-center items-center text-center cursor-pointer transition tap-press overflow-y-auto overscroll-contain relative"
      >
        <div class="space-y-4 w-full">
          <div class="text-3xl sm:text-5xl font-bold font-serif text-[#181A1B] jp-font tracking-wide">
            ${card.front}
          </div>
          ${!isFlipped ? `
            <div class="pt-6 text-neutral-400 font-mono text-xs animate-pulse">
              [ Tocca o premi <kbd class="px-1.5 py-0.5 border border-black/20 bg-neutral-100 text-black">Spazio</kbd> ]
            </div>
          ` : ''}
        </div>

        ${isFlipped ? `
          <div class="w-full mt-6 pt-6 border-t-2 border-black/10 space-y-4 animate-info-fade">
            ${card.reading ? `<div class="text-xl sm:text-2xl font-bold text-[#1E2C3A] jp-font">${card.reading}</div>` : ''}
            ${card.meaning ? `<div class="text-base sm:text-lg font-sans font-semibold text-neutral-800">${card.meaning}</div>` : ''}
            ${card.notes ? `<div class="text-xs font-mono text-neutral-500 pt-2 border-t border-black/5">${card.notes}</div>` : ''}
          </div>
        ` : ''}
      </div>

      <!-- Bottom Anki 4-Button Bar -->
      <div class="flex-shrink-0 pt-2 border-t border-black/10">
        ${!isFlipped ? `
          <button 
            onclick="window.srsFlipCard()" 
            class="w-full py-3 bg-[#181A1B] text-white font-mono text-xs sm:text-sm font-bold uppercase tracking-wider transition tap-press active:scale-[0.98] flex items-center justify-center gap-2"
          >
            <span>Mostra Risposta</span>
            <kbd class="hidden sm:inline px-1 py-0.2 bg-white/20 text-[10px] rounded">Spazio</kbd>
          </button>
        ` : `
          <div class="grid grid-cols-4 gap-1.5 sm:gap-2 font-mono">
            <button onclick="window.srsAnswerCard(1)" class="py-2 sm:py-2.5 px-1 bg-[#FDF1EF] hover:bg-[#C23B22] text-[#C23B22] hover:text-white border border-[#C23B22]/40 text-center transition tap-press active:scale-95 flex flex-col items-center justify-center">
              <span class="text-[10px] sm:text-xs opacity-70">${ivls.again}</span>
              <span class="text-xs sm:text-sm font-bold uppercase">Ripeti</span>
              <span class="hidden sm:inline text-[9px] opacity-50 mt-0.5">[1]</span>
            </button>
            <button onclick="window.srsAnswerCard(2)" class="py-2 sm:py-2.5 px-1 bg-[#FFFBEB] hover:bg-[#D97706] text-[#D97706] hover:text-white border border-[#D97706]/40 text-center transition tap-press active:scale-95 flex flex-col items-center justify-center">
              <span class="text-[10px] sm:text-xs opacity-70">${ivls.hard}</span>
              <span class="text-xs sm:text-sm font-bold uppercase">Difficile</span>
              <span class="hidden sm:inline text-[9px] opacity-50 mt-0.5">[2]</span>
            </button>
            <button onclick="window.srsAnswerCard(3)" class="py-2 sm:py-2.5 px-1 bg-[#EEF7F1] hover:bg-[#264332] text-[#264332] hover:text-white border border-[#264332]/40 text-center transition tap-press active:scale-95 flex flex-col items-center justify-center font-bold">
              <span class="text-[10px] sm:text-xs opacity-70">${ivls.good}</span>
              <span class="text-xs sm:text-sm font-bold uppercase">Buono</span>
              <span class="hidden sm:inline text-[9px] opacity-50 mt-0.5">[3]</span>
            </button>
            <button onclick="window.srsAnswerCard(4)" class="py-2 sm:py-2.5 px-1 bg-[#EFF6FF] hover:bg-[#2563EB] text-[#2563EB] hover:text-white border border-[#2563EB]/40 text-center transition tap-press active:scale-95 flex flex-col items-center justify-center">
              <span class="text-[10px] sm:text-xs opacity-70">${ivls.easy}</span>
              <span class="text-xs sm:text-sm font-bold uppercase">Facile</span>
              <span class="hidden sm:inline text-[9px] opacity-50 mt-0.5">[4]</span>
            </button>
          </div>
        `}
      </div>
    </div>
  `;
}

export function renderCompletion(container, onRestart) {
  if (!container) return;
  container.innerHTML = `
    <div class="h-full flex flex-col items-center justify-center p-6 text-center space-y-4 animate-info-fade max-w-md mx-auto">
      <div class="w-12 h-12 rounded-full bg-[#EEF7F1] border border-[#264332]/30 flex items-center justify-center text-xl text-[#264332]">
        ✓
      </div>
      <div class="space-y-1">
        <h3 class="text-base font-bold font-editorial-serif uppercase text-[#181A1B]">Sessione di Test Completata</h3>
        <p class="text-xs text-neutral-500 font-mono">Hai testato tutte le 10 carte del lotto dimostrativo.</p>
      </div>
      <button 
        id="btnRestartSrsDemo"
        class="py-2.5 px-6 bg-[#181A1B] text-white font-mono text-xs font-bold uppercase tracking-wider transition tap-press active:scale-95"
      >
        Ricomincia Test →
      </button>
    </div>
  `;
  const btn = document.getElementById('btnRestartSrsDemo');
  if (btn && onRestart) {
    btn.onclick = onRestart;
  }
}
