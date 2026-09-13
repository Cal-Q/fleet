// static/js/modules/exams.js — MEXT Exam Drill Engine & Branch Manager
// Strictly <= 200 lines invariant.

import { loadInterview } from "./interview.js";
import { renderExamResults, loadExamAnalytics } from "./exam_analytics.js";
import { initExamNotes, getUserComment, getAllUserComments, saveQuestionNote } from "./exam_notes.js";
import { startPacingTimer, stopPacingTimer, getElapsedSeconds, updatePacingUI } from "./exam_pacing.js";

export { loadExamAnalytics, saveQuestionNote };

let currentQuestions = [];
let userAnswers = {};
let currentSection = "all";

export function getUserAnswer(qid) { return userAnswers[qid] || ""; }

export function resetExam(section = null) {
  const targetSection = section || currentSection || "all";
  userAnswers = {};
  try { localStorage.removeItem("mext_exam_answers"); } catch (e) {}
  loadExam(targetSection, true);
}

export async function loadExam(section = "all", clean = false) {
  currentSection = section;
  highlightSectionBtn(section);

  const url = (section === "all") ? "/api/exams/questions" : `/api/exams/questions?section=${section}`;
  const res = await fetch(url);
  currentQuestions = await res.json();

  const container = document.getElementById("examContainer");
  const resultsBox = document.getElementById("examResultsBox");
  if (!container) return;
  container.innerHTML = "";
  if (resultsBox) resultsBox.classList.add("hidden");

  const titleMap = {
    all: "Tutte le Sezioni (14Q)",
    mock: "⚡ Simulazione Completa (30Q: 12A + 10B + 8C)",
    A: "Parte 1: A (初級 - N5/N4)",
    B: "Parte 2: B (中級 - N3/N2)",
    C: "Parte 3: C (上級 - N1)"
  };
  const leafTitle = document.getElementById("drillLeafTitle");
  if (leafTitle) leafTitle.innerText = `Quesiti Prove Scritte • ${titleMap[section] || section}`;

  const today = new Date().toISOString().split("T")[0];
  if (clean || localStorage.getItem("mext_exam_date") !== today) {
    userAnswers = {};
    try { localStorage.removeItem("mext_exam_answers"); localStorage.setItem("mext_exam_date", today); } catch (e) {}
  } else {
    try { userAnswers = { ...JSON.parse(localStorage.getItem("mext_exam_answers") || "{}") }; } catch (e) { userAnswers = {}; }
  }

  const serverNotes = {};
  currentQuestions.forEach(q => { if (q.saved_comment) serverNotes[q.id] = q.saved_comment; });
  initExamNotes(serverNotes);

  currentQuestions.forEach((q, idx) => {
    const card = document.createElement("div");
    card.className = "p-4 md:p-5 border border-black/10 bg-white space-y-3.5";
    card.id = `q_card_${q.id}`;
    const sel = userAnswers[q.id] || "";
    const note = getUserComment(q.id);

    card.innerHTML = `
      <div class="flex items-center justify-between text-xs md:text-sm text-neutral-500 border-b border-black/5 pb-2 font-mono">
        <span class="font-bold text-[#E63920]">Q.${String(idx + 1).padStart(2, "0")} • SEZ. ${q.section} (${q.level || "N/A"})</span>
        <span id="q_badge_${q.id}" class="${sel ? "text-xs font-mono px-2 py-0.5 border border-[#264332]/30 bg-[#EEF7F1] text-[#264332] font-bold" : "text-xs font-mono px-2 py-0.5 border border-black/10 bg-[#FAF8F5] text-neutral-400"}">${sel ? `✓ Risposta: ${sel}` : "In attesa"}</span>
      </div>
      <div class="jp-mincho text-base md:text-xl text-[#111111] font-medium whitespace-pre-line leading-relaxed tracking-wide">${q.question}</div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-2.5 pt-1 font-mono text-xs md:text-sm">
        ${["A", "B", "C", "D"].filter(k => q.options && q.options[k]).map(k => {
          const isSel = (sel === k);
          return `<button type="button" id="opt_${q.id}_${k}" onclick="window.selectExamOption('${q.id}', '${k}')" class="exam-opt-card flex items-center gap-3 p-3 md:p-3.5 ${isSel ? "border-2 border-[#181A1B] bg-[#181A1B] text-white shadow-sm" : "border border-black/10 bg-[#FAF9F6] hover:bg-white hover:border-black/30"} cursor-pointer transition-all duration-100 tap-press active:scale-[0.98] text-left">
            <span class="opt-indicator w-6 h-6 md:w-7 md:h-7 flex-shrink-0 flex items-center justify-center border ${isSel ? "border-white bg-white text-[#181A1B]" : "border-black/20 bg-white text-neutral-600"} text-xs md:text-sm font-bold font-mono">${isSel ? "✓" : k}</span>
            <span class="jp-mincho ${isSel ? "text-white font-bold" : "text-[#111111] font-medium"} text-sm md:text-base flex-1 leading-snug">${q.options[k]}</span>
          </button>`;
        }).join("")}
      </div>
      <div class="pt-2 border-t border-black/5 space-y-1">
        <div class="flex items-center justify-between text-xs font-mono text-neutral-500">
          <span class="flex items-center gap-1 font-bold text-[#181A1B]"><span>📝</span><span>Nota / Ragionamento per revisione:</span></span>
          <span id="note_status_${q.id}" class="text-[11px] font-mono text-neutral-400">Salvataggio automatico</span>
        </div>
        <textarea id="note_${q.id}" rows="2" placeholder="Scrivi qui il tuo ragionamento o dubbi per questa prova..." oninput="window.saveQuestionNote('${q.id}')" class="w-full p-2.5 text-xs md:text-sm border border-black/10 bg-[#FAF9F6] focus:bg-white focus:border-black focus:outline-none transition rounded-none resize-y font-sans leading-relaxed"></textarea>
        ${(note && !note.includes('Commento aggiornato')) ? `<details class="text-[11px] font-mono text-neutral-500 pt-0.5"><summary class="cursor-pointer hover:text-black font-bold select-none tap-press">📜 Appunto sessione precedente (clicca per mostrare)</summary><div class="p-2 mt-1 bg-neutral-100 border border-black/5 text-neutral-700 font-sans italic whitespace-pre-line">${note}</div></details>` : ''}
      </div>
    `;
    container.appendChild(card);
  });

  const bottomBar = document.createElement("div");
  bottomBar.className = "p-4 border border-black/10 bg-[#FAF8F5] flex flex-col sm:flex-row sm:items-center justify-between gap-3 mt-4";
  bottomBar.innerHTML = `
    <div>
      <div id="leafBottomCount" class="text-sm md:text-base font-mono font-bold text-[#181A1B]">0 / ${currentQuestions.length} completati</div>
      <div class="text-xs md:text-sm text-neutral-500 font-mono">Tutte le risposte e note vengono salvate per la revisione.</div>
    </div>
    <div class="flex items-center gap-2">
      <button onclick="window.resetExam('${section}')" class="px-3.5 py-2.5 bg-white border border-black/20 hover:border-black text-neutral-700 font-mono font-bold text-xs md:text-sm uppercase transition tap-press active:scale-95">🔄 Azzera</button>
      <button onclick="submitExam()" class="px-5 py-2.5 bg-[#264332] hover:bg-[#1b3024] text-white font-mono font-bold text-xs md:text-sm uppercase transition tap-press active:scale-95 shadow-sm">Invia Esame & Correggi →</button>
    </div>
  `;
  container.appendChild(bottomBar);

  updateProgressUI();

  startPacingTimer((sec, timeStr) => {
    const tEl = document.getElementById("timeElapsed");
    if (tEl) tEl.innerText = timeStr;
    const ansCount = currentQuestions.filter(q => userAnswers[q.id]).length;
    updatePacingUI(sec, ansCount, currentQuestions.length, currentSection);
  });
}

function highlightSectionBtn(sec) {
  ["all", "mock", "A", "B", "C"].forEach(s => {
    const b = document.getElementById("btn_sec_" + s);
    if (!b) return;
    const col = (s === "mock") ? "col-span-2 " : "";
    b.className = `${col}px-2.5 py-2 text-xs md:text-sm font-bold uppercase transition tap-press active:scale-95 text-center ` +
      (s === sec ? "bg-[#181A1B] text-white shadow-sm" : "bg-[#FAF8F5] border border-black/10 hover:border-black text-neutral-700");
  });
}

export function selectExamOption(qid, optKey) {
  userAnswers[qid] = optKey;
  try { localStorage.setItem("mext_exam_answers", JSON.stringify(userAnswers)); } catch (e) {}

  ["A", "B", "C", "D"].forEach(k => {
    const el = document.getElementById(`opt_${qid}_${k}`);
    if (!el) return;
    const ind = el.querySelector(".opt-indicator"), txt = el.querySelector(".jp-mincho, .jp-font"), isSel = (k === optKey);
    el.className = `exam-opt-card flex items-center gap-3 p-3 md:p-3.5 ${isSel ? "border-2 border-[#181A1B] bg-[#181A1B] text-white shadow-sm" : "border border-black/10 bg-[#FAF9F6] hover:bg-white hover:border-black/30"} cursor-pointer transition-all duration-100 tap-press active:scale-[0.98] text-left`;
    if (txt) txt.className = `jp-mincho ${isSel ? "text-white font-bold" : "text-[#111111] font-medium"} text-sm md:text-base flex-1 leading-snug`;
    if (ind) {
      ind.className = `opt-indicator w-6 h-6 md:w-7 md:h-7 flex-shrink-0 flex items-center justify-center border ${isSel ? "border-white bg-white text-[#181A1B]" : "border-black/20 bg-white text-neutral-600"} text-xs md:text-sm font-bold font-mono`;
      ind.innerText = isSel ? "✓" : k;
    }
  });

  const badge = document.getElementById(`q_badge_${qid}`);
  if (badge) {
    badge.className = "text-xs font-mono px-2 py-0.5 border border-[#264332]/30 bg-[#EEF7F1] text-[#264332] font-bold";
    badge.innerText = `✓ Risposta: ${optKey}`;
  }
  updateProgressUI();
}

function updateProgressUI() {
  const answered = currentQuestions.filter(q => userAnswers[q.id]).length;
  const total = currentQuestions.length;
  const pct = total ? Math.round((answered / total) * 100) : 0;
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.innerText = val; };
  set("drillAnswerProgress", `${answered} / ${total} (${pct}%)`);
  set("trunkProgressPill", `${answered}/${total}`);
  set("submitExamBtn", answered === total ? "Invia Esame & Correggi →" : `Invia Esame (${answered}/${total}) →`);
  set("leafBottomCount", `${answered} / ${total} completati`);
  updatePacingUI(getElapsedSeconds(), answered, total, currentSection);
}

export async function submitExam() {
  const answered = currentQuestions.filter(q => userAnswers[q.id]).length, total = currentQuestions.length;
  if (answered < total && !confirm(`Attenzione: ci sono ancora ${total - answered} quesiti senza risposta.\nVuoi consegnare comunque? Le risposte omesse risulteranno errate.`)) return;
  stopPacingTimer();
  const spent = getElapsedSeconds();
  const answers = {};
  currentQuestions.forEach(q => { answers[q.id] = userAnswers[q.id] || ""; });
  const comments = getAllUserComments();

  const res = await fetch("/api/exams/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers, comments, time_spent_seconds: spent })
  });
  const result = await res.json();
  try { localStorage.removeItem("mext_exam_answers"); } catch (e) {}
  userAnswers = {};
  loadExamAnalytics();
  if (typeof window.markRoutineSlotDone === "function") window.markRoutineSlotDone("slot4");
  renderExamResults(result, spent, currentSection);
}

export function switchExamBranch(branch) {
  ["drill", "interview", "analytics"].forEach(b => {
    const leaf = document.getElementById("leaf_exam_" + b), btn = document.getElementById("branch_btn_exam_" + b), active = (b === branch);
    if (leaf) leaf.classList.toggle("hidden", !active);
    if (btn) { btn.classList.toggle("bg-white", active); btn.classList.toggle("opacity-100", active); btn.classList.toggle("opacity-70", !active); }
  });
  if (branch === "interview") loadInterview();
  else if (branch === "analytics") loadExamAnalytics();
  else if (branch === "drill" && !currentQuestions.length) loadExam(currentSection);
}
