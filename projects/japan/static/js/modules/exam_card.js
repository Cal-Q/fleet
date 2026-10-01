// static/js/modules/exam_card.js — Single-Question Card & Progression Rail Renderer
// Strictly <= 200 lines invariant.

import { getUserComment } from "./exam_notes.js";
import {
  getUserAnswer,
  getConfidence,
  getUnknownChars,
  isMissingPartsActive,
} from "./exam_state.js";
import {
  buildClickableText,
  buildMissingBanner,
  buildUnknownChips,
  buildOptionsGrid,
  buildConfidenceBar,
  buildDontKnowButton,
} from "./exam_card_html.js";

let noteOpen = false;

export function isNoteOpen() {
  return noteOpen;
}

export function toggleNoteState() {
  noteOpen = !noteOpen;
  const drawer = document.getElementById("noteDrawer");
  const txt = document.getElementById("noteToggleText");
  if (drawer) drawer.classList.toggle("hidden", !noteOpen);
  if (txt) {
    txt.innerText = noteOpen ? "Nascondi appunto" : "📝 Aggiungi appunto / ragionamento...";
  }
  return noteOpen;
}

export function renderQuestionRail(questions, currentIndex) {
  const rail = document.getElementById("examQuestionRail");
  if (!rail) return;
  rail.innerHTML = questions
    .map((q, idx) => {
      const isCur = idx === currentIndex;
      const ans = getUserAnswer(q.id);
      let cls = "bg-[#FAF8F5] text-neutral-500 border border-black/10 hover:border-black";
      if (isCur) {
        cls = "bg-[#181A1B] text-white font-bold border-2 border-[#181A1B] shadow-2xs scale-105";
      } else if (ans === "DONT_KNOW") {
        cls = "bg-[#FEF3C7] text-[#92400E] font-bold border border-[#F59E0B]/40";
      } else if (ans) {
        cls = "bg-[#EEF7F1] text-[#264332] font-bold border border-[#264332]/30";
      }
      const num = idx + 1;
      return (
        `<button type="button" onclick="window.goToQuestion(${idx})" ` +
        `class="w-7 h-7 flex-shrink-0 flex items-center justify-center font-mono ` +
        `text-xs transition tap-press active:scale-95 ${cls}">${num}</button>`
      );
    })
    .join("");
}

function buildHeaderHtml(currentIndex, totalCount, q, conf, isDontKnow, sel) {
  const qNum = String(currentIndex + 1).padStart(2, "0");
  const tNum = String(totalCount).padStart(2, "0");
  const task = q.task_type || "PROVA";
  const sec = q.section;
  const lvl = q.level || "N/A";
  const confHtml = conf
    ? `<span class="px-1.5 py-0.5 bg-[#FAF8F5] border border-black/10 ` +
      `font-mono text-[10px] text-neutral-600 font-bold">Sicurezza: ${conf}/9</span>`
    : "";
  let bCls = "border-black/10 bg-[#FAF8F5] text-neutral-400";
  let bTxt = "In attesa";
  if (isDontKnow) {
    bCls = "border-[#F59E0B]/40 bg-[#FEF3C7] text-[#92400E] font-bold";
    bTxt = "? Non lo so";
  } else if (sel) {
    bCls = "border-[#264332]/30 bg-[#EEF7F1] text-[#264332] font-bold";
    bTxt = `✓ Risposta: ${sel}`;
  }

  return (
    `<div class="flex items-center justify-between text-xs font-mono border-b ` +
    `border-black/5 pb-2 text-neutral-500"><div class="flex items-center gap-2">` +
    `<span class="font-bold text-[#E63920]">Q.${qNum} / ${tNum}</span>` +
    `<span class="px-2 py-0.5 bg-[#FAF8F5] border border-black/10 font-bold ` +
    `text-neutral-700">${task}</span><span class="text-neutral-400">SEZ. ${sec} ` +
    `(${lvl})</span></div><div class="flex items-center gap-1.5">${confHtml}` +
    `<span class="px-2 py-0.5 border ${bCls}">${bTxt}</span></div></div>`
  );
}

function buildNoteHtml(qid, note) {
  const tText = noteOpen || note ? "📝 Nascondi appunto" : "📝 Aggiungi appunto / ragionamento...";
  const dCls = noteOpen || note ? "" : "hidden";
  return (
    `<div class="pt-1 border-t border-black/5 space-y-1">` +
    `<button type="button" onclick="window.toggleCurrentNote()" ` +
    `class="text-xs font-mono text-neutral-500 hover:text-black ` +
    `flex items-center gap-1 font-bold">` +
    `<span id="noteToggleText">${tText}</span></button>` +
    `<div id="noteDrawer" class="${dCls} space-y-1">` +
    `<textarea id="note_${qid}" rows="2" placeholder="Scrivi note per questa prova..." ` +
    `oninput="window.saveQuestionNote('${qid}')" class="w-full p-2 text-xs border ` +
    `border-black/10 bg-[#FAF9F6] focus:bg-white focus:border-black focus:outline-none ` +
    `transition resize-none font-sans">${note}</textarea></div></div>`
  );
}

function buildFooterHtml(currentIndex, totalCount, isLast) {
  const prevDis = currentIndex === 0 ? "disabled class='opacity-40 cursor-not-allowed'" : "";
  const prevCls = "px-3 py-1.5 bg-[#FAF8F5] border border-black/10 font-bold transition tap-press";
  const nextCls = isLast ? "bg-[#264332] text-white" : "bg-[#181A1B] text-white";
  const nextTxt = isLast ? "Consegna Prova →" : "Successiva →";

  return (
    `<footer class="flex-shrink-0 p-2.5 bg-white border border-black/10 flex items-center ` +
    `justify-between gap-2 font-mono text-xs mt-2"><button onclick="window.prevQuestion()" ` +
    `${prevDis} class="${prevCls}">← Precedente</button><span class="text-neutral-500 font-bold">` +
    `${currentIndex + 1} di ${totalCount}</span><button onclick="window.nextQuestion()" ` +
    `class="px-3.5 py-1.5 ${nextCls} font-bold transition tap-press active:scale-95 shadow-2xs">` +
    `${nextTxt}</button></footer>`
  );
}

export function renderActiveQuestion(questions, currentIndex) {
  const container = document.getElementById("examSingleContainer");
  if (!container || !questions.length) return;
  const q = questions[currentIndex];
  const sel = getUserAnswer(q.id);
  const conf = getConfidence(q.id);
  const unknowns = getUnknownChars(q.id);
  const isMissing = isMissingPartsActive();
  const note = getUserComment(q.id);
  const isLast = currentIndex === questions.length - 1;
  const isDontKnow = sel === "DONT_KNOW";

  const headHtml = buildHeaderHtml(currentIndex, questions.length, q, conf, isDontKnow, sel);
  const missHtml = buildMissingBanner(isMissing);
  const qText = buildClickableText(q.id, q.question, unknowns, isMissing);
  const unkHtml = buildUnknownChips(q.id, unknowns);
  const optHtml = buildOptionsGrid(q, sel, unknowns, isMissing);
  const dkHtml = buildDontKnowButton(q.id, isDontKnow);
  const confHtml = buildConfidenceBar(conf);
  const noteHtml = buildNoteHtml(q.id, note);
  const footHtml = buildFooterHtml(currentIndex, questions.length, isLast);

  container.innerHTML = (
    `<div class="p-3 md:p-5 bg-white border border-black/10 flex flex-col justify-between ` +
    `space-y-3 shadow-2xs">${headHtml}${missHtml}` +
    `<div class="jp-mincho text-lg md:text-2xl text-[#111111] font-medium whitespace-pre-line ` +
    `leading-relaxed tracking-wide py-1 select-text">${qText}</div>` +
    `${unkHtml}${optHtml}${dkHtml}${confHtml}${noteHtml}</div>${footHtml}`
  );
}
