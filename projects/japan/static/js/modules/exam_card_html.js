// static/js/modules/exam_card_html.js — HTML Builders for Exam Card View
// Strictly <= 200 lines invariant.

export function buildClickableText(qid, text, unknowns, isMissing) {
  if (!isMissing) return text;
  return Array.from(text)
    .map((ch) => {
      if (ch === "\n") return "<br>";
      if (/\s/.test(ch)) return ch;
      const isU = unknowns.includes(ch);
      const act =
        "clickable-char bg-red-200 text-red-900 underline font-bold px-0.5 " +
        "rounded cursor-pointer";
      const norm =
        "clickable-char hover:bg-amber-200 cursor-pointer px-0.5 rounded transition";
      const cls = isU ? act : norm;
      return `<span onclick="window.onCharClick('${qid}', '${ch}')" class="${cls}">${ch}</span>`;
    })
    .join("");
}

export function buildMissingBanner(isMissing) {
  if (!isMissing) return "";
  return (
    `<div class="p-2 bg-[#FFFBEB] border border-[#D97706]/40 text-[#92400E] ` +
    `text-xs font-mono flex items-center justify-between rounded">` +
    `<span>⚠️ <b>PARTI MANCANTI ATTIVA:</b> Timer in pausa. Clicca sui caratteri.</span>` +
    `<button onclick="window.toggleMissingPartsMode()" ` +
    `class="px-2 py-0.5 bg-[#92400E] text-white font-bold text-[10px] rounded">` +
    `Termina Modalità</button></div>`
  );
}

export function buildUnknownChips(qid, unknowns) {
  if (!unknowns || !unknowns.length) return "";
  const chips = unknowns
    .map(
      (c) =>
        `<span class="inline-flex items-center gap-1 px-1.5 py-0.5 bg-red-100 ` +
        `text-red-800 border border-red-300 rounded font-bold">${c}` +
        `<button type="button" onclick="window.onCharClick('${qid}', '${c}')" ` +
        `class="text-red-500 hover:text-black">×</button></span>`
    )
    .join("");
  return (
    `<div class="flex flex-wrap items-center gap-1.5 p-1.5 bg-[#FAF8F5] border ` +
    `border-black/10 text-xs font-mono"><span class="font-bold text-red-800">` +
    `Caratteri sconosciuti (${unknowns.length}):</span>${chips}</div>`
  );
}

export function buildOptionsGrid(q, sel, unknowns, isMissing) {
  const hotkeys = { A: "Q", B: "W", C: "A", D: "S" };
  const keys = ["A", "B", "C", "D"].filter((k) => q.options && q.options[k]);
  return (
    `<div class="grid grid-cols-1 sm:grid-cols-2 gap-2 font-mono text-xs md:text-sm">` +
    keys
      .map((k) => {
        const isSel = sel === k;
        const bCls = isSel
          ? "border-2 border-[#181A1B] bg-[#181A1B] text-white shadow-2xs"
          : "border border-black/10 bg-[#FAF9F6] hover:bg-white hover:border-black/30";
        const kCls = isSel
          ? "border-white bg-white text-[#181A1B]"
          : "border-black/20 bg-white text-neutral-600";
        const tCls = isSel ? "text-white font-bold" : "text-[#111111] font-medium";
        const optHtml = buildClickableText(q.id, q.options[k], unknowns, isMissing);
        return (
          `<button type="button" onclick="window.selectExamOption('${q.id}', '${k}')" ` +
          `class="exam-opt-card flex items-center gap-2.5 p-2.5 md:p-3 ${bCls} ` +
          `cursor-pointer transition tap-press active:scale-[0.98] text-left">` +
          `<span class="w-6 h-6 flex-shrink-0 flex items-center justify-center ` +
          `border ${kCls} text-xs font-bold font-mono">${hotkeys[k]}</span>` +
          `<span class="jp-mincho ${tCls} text-sm md:text-base flex-1 leading-snug">` +
          `${optHtml}</span></button>`
        );
      })
      .join("") +
    `</div>`
  );
}

export function buildConfidenceBar(conf) {
  const label = conf ? `Livello ${conf} / 9` : "Non impostata";
  const numBtns = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    .map((n) => {
      const isC = conf === n;
      const cls = isC
        ? "bg-[#181A1B] text-white border-[#181A1B] shadow-2xs"
        : "bg-[#FAF8F5] border-black/10 hover:border-black text-neutral-600";
      return (
        `<button type="button" onclick="window.setConfidenceLevel(${n})" ` +
        `class="py-1 text-center font-bold transition tap-press active:scale-95 border ${cls}">` +
        `${n}</button>`
      );
    })
    .join("");

  return (
    `<div class="pt-2 border-t border-black/5 space-y-1">` +
    `<div class="flex items-center justify-between text-[11px] font-mono text-neutral-500">` +
    `<span>Sicurezza risposta (Tasti 1–9):</span>` +
    `<span class="font-bold font-mono ` +
    `${conf ? "text-[#181A1B]" : "text-neutral-400"}">${label}</span>` +
    `</div><div class="grid grid-cols-9 gap-1 font-mono text-xs">${numBtns}</div></div>`
  );
}

export function buildDontKnowButton(qid, isDontKnow) {
  const btnCls = isDontKnow
    ? "border-2 border-[#D97706] bg-[#D97706] text-white font-bold shadow-2xs"
    : "border-black/10 bg-[#FAF8F5] hover:bg-[#FFFBEB] hover:border-[#D97706]/40 text-[#92400E]";
  const boxCls = isDontKnow
    ? "border-white bg-white text-[#D97706]"
    : "border-[#D97706]/40 bg-white text-[#92400E]";

  return (
    `<button type="button" onclick="window.selectExamOption('${qid}', 'DONT_KNOW')" ` +
    `class="exam-dontknow-btn w-full flex items-center justify-between p-2 md:p-2.5 border ` +
    `transition tap-press active:scale-[0.99] text-xs font-mono ${btnCls}">` +
    `<div class="flex items-center gap-2">` +
    `<span class="w-5 h-5 flex items-center justify-center border ${boxCls} font-bold">[X]</span>` +
    `<span class="font-bold">❓ Risposta: "Non lo so" (segnala lacuna)</span>` +
    `</div><span class="font-bold">${isDontKnow ? "✓ Selezionato" : ""}</span></button>`
  );
}

export function updateMissingPartsBtnUI(active) {
  const btn = document.getElementById("btnToggleMissingParts");
  if (!btn) return;
  const base = "px-2 py-0.5 border font-bold transition tap-press active:scale-95 text-xs";
  if (active) {
    btn.className = `${base} border-[#D97706] bg-[#FEF3C7] text-[#92400E] shadow-2xs`;
    btn.innerHTML = '<span>🔍</span><span id="missingPartsLabel">Parti Mancanti: <b>ON</b></span>';
  } else {
    btn.className = `${base} border-black/20 bg-white hover:border-black text-neutral-700`;
    btn.innerHTML = '<span>🔍</span><span id="missingPartsLabel">Parti Mancanti: OFF</span>';
  }
}

