// static/js/modules/exam_card.js — Single-Question Card & Progression Rail Renderer
// Strictly <= 200 lines invariant.

import { getUserComment, saveQuestionNote } from "./exam_notes.js";

let noteOpen = false;

export function isNoteOpen() { return noteOpen; }

export function toggleNoteState() {
  noteOpen = !noteOpen;
  const drawer = document.getElementById("noteDrawer");
  const txt = document.getElementById("noteToggleText");
  if (drawer) drawer.classList.toggle("hidden", !noteOpen);
  if (txt) txt.innerText = noteOpen ? "Nascondi appunto" : "📝 Aggiungi appunto / ragionamento...";
  return noteOpen;
}

export function renderQuestionRail(questions, currentIndex, userAnswers) {
  const rail = document.getElementById("examQuestionRail");
  if (!rail) return;
  rail.innerHTML = questions.map((q, idx) => {
    const isCur = (idx === currentIndex), ans = userAnswers[q.id];
    let cls = isCur
      ? "bg-[#181A1B] text-white font-bold border-2 border-[#181A1B] shadow-2xs scale-105"
      : (ans ? "bg-[#EEF7F1] text-[#264332] font-bold border border-[#264332]/30" : "bg-[#FAF8F5] text-neutral-500 border border-black/10 hover:border-black");
    return `<button type="button" onclick="window.goToQuestion(${idx})" class="w-7 h-7 flex-shrink-0 flex items-center justify-center font-mono text-xs transition tap-press active:scale-95 ${cls}">${idx + 1}</button>`;
  }).join("");
}

export function renderActiveQuestion(questions, currentIndex, userAnswers) {
  const container = document.getElementById("examSingleContainer");
  if (!container || !questions.length) return;
  const q = questions[currentIndex];
  const sel = userAnswers[q.id] || "";
  const note = getUserComment(q.id);
  const isLast = (currentIndex === questions.length - 1);

  container.innerHTML = `
    <div class="p-4 md:p-6 bg-white border border-black/10 flex flex-col justify-between space-y-4 shadow-2xs">
      <div class="flex items-center justify-between text-xs font-mono border-b border-black/5 pb-2 text-neutral-500">
        <div class="flex items-center gap-2">
          <span class="font-bold text-[#E63920]">Q.${String(currentIndex + 1).padStart(2, "0")} / ${String(questions.length).padStart(2, "0")}</span>
          <span class="px-2 py-0.5 bg-[#FAF8F5] border border-black/10 font-bold text-neutral-700">${q.task_type || "PROVA"}</span>
          <span class="text-neutral-400">SEZ. ${q.section} (${q.level || "N/A"})</span>
        </div>
        <span class="${sel ? "px-2 py-0.5 border border-[#264332]/30 bg-[#EEF7F1] text-[#264332] font-bold" : "px-2 py-0.5 border border-black/10 bg-[#FAF8F5] text-neutral-400"}">${sel ? `✓ Risposta: ${sel}` : "In attesa"}</span>
      </div>

      <div class="jp-mincho text-xl md:text-2xl text-[#111111] font-medium whitespace-pre-line leading-relaxed tracking-wide py-2 select-text">${q.question}</div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 font-mono text-xs md:text-sm">
        ${["A", "B", "C", "D"].filter(k => q.options && q.options[k]).map((k, kIdx) => {
          const isSel = (sel === k);
          return `<button type="button" onclick="window.selectExamOption('${q.id}', '${k}')" class="exam-opt-card flex items-center gap-3 p-3.5 ${isSel ? "border-2 border-[#181A1B] bg-[#181A1B] text-white shadow-2xs" : "border border-black/10 bg-[#FAF9F6] hover:bg-white hover:border-black/30"} cursor-pointer transition tap-press active:scale-[0.98] text-left">
            <span class="w-6 h-6 md:w-7 md:h-7 flex-shrink-0 flex items-center justify-center border ${isSel ? "border-white bg-white text-[#181A1B]" : "border-black/20 bg-white text-neutral-600"} text-xs font-bold font-mono">${isSel ? "✓" : (kIdx + 1)}</span>
            <span class="jp-mincho ${isSel ? "text-white font-bold" : "text-[#111111] font-medium"} text-sm md:text-base flex-1 leading-snug">${q.options[k]}</span>
          </button>`;
        }).join("")}
      </div>

      <div class="pt-2 border-t border-black/5 space-y-2">
        <button type="button" onclick="window.toggleCurrentNote()" class="text-xs font-mono text-neutral-500 hover:text-black flex items-center gap-1 font-bold">
          <span id="noteToggleText">${noteOpen || note ? "📝 Nascondi appunto" : "📝 Aggiungi appunto / ragionamento..."}</span>
        </button>
        <div id="noteDrawer" class="${(noteOpen || note) ? "" : "hidden"} space-y-1">
          <textarea id="note_${q.id}" rows="2" placeholder="Scrivi note per questa prova..." oninput="window.saveQuestionNote('${q.id}')" class="w-full p-2.5 text-xs border border-black/10 bg-[#FAF9F6] focus:bg-white focus:border-black focus:outline-none transition resize-none font-sans">${note}</textarea>
          <span id="note_status_${q.id}" class="text-[10px] font-mono text-neutral-400">Salvataggio automatico per revisione</span>
        </div>
      </div>
    </div>

    <footer class="flex-shrink-0 p-3 bg-white border border-black/10 flex items-center justify-between gap-2 font-mono text-xs mt-2">
      <button onclick="window.prevQuestion()" ${currentIndex === 0 ? "disabled class='opacity-40 cursor-not-allowed'" : "class='hover:border-black'"} class="px-3.5 py-2 bg-[#FAF8F5] border border-black/10 font-bold transition tap-press active:scale-95">← Precedente</button>
      <span class="text-neutral-500 font-bold">${currentIndex + 1} di ${questions.length}</span>
      <div class="flex items-center gap-2">
        <button onclick="window.nextQuestion()" class="px-4 py-2 ${isLast ? "bg-[#264332] text-white" : "bg-[#181A1B] text-white"} font-bold transition tap-press active:scale-95 shadow-2xs">${isLast ? "Consegna Prova →" : "Successiva →"}</button>
      </div>
    </footer>
  `;
}
