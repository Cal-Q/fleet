// static/js/modules/exams.js — MEXT Single-Question Focused Runner Engine
// Strictly <= 200 lines invariant.

import { loadExamAnalytics } from "./exam_analytics.js";
import { initExamNotes, saveQuestionNote } from "./exam_notes.js";
import { highlightSectionBtn, switchExamBranch as switchBranchModule } from "./exam_branches.js";
import { submitExamSession } from "./exam_submit.js";
import { initExamKeybindings } from "./exam_keybindings.js";
import {
  startPacingTimer,
  pausePacingTimer,
  resumePacingTimer,
  resetPacingTimer,
  getElapsedSeconds,
  updatePacingUI,
} from "./exam_pacing.js";
import { renderQuestionRail, renderActiveQuestion, toggleNoteState } from "./exam_card.js";
import { updateMissingPartsBtnUI } from "./exam_card_html.js";
import {
  loadExamStateFromStorage,
  clearExamStateStorage,
  getUserAnswer,
  setUserAnswer,
  getConfidence,
  setConfidence,
  getUnknownChars,
  toggleUnknownChar,
  isMissingPartsActive,
  setMissingPartsActive,
} from "./exam_state.js";

export { loadExamAnalytics, saveQuestionNote, getUserAnswer };

let currentQuestions = [];
let currentSection = "A";
let currentIndex = 0;
let currentBatch = 0;

export function confirmResetExamTimer() {
  if (window.confirm("Vuoi davvero azzerare il timer della prova corrente?")) {
    resetPacingTimer();
  }
}

export function toggleMissingPartsMode() {
  const active = !isMissingPartsActive();
  setMissingPartsActive(active);
  if (active) {
    pausePacingTimer();
  } else {
    resumePacingTimer();
  }
  updateMissingPartsBtnUI(active);
  renderExamView();
}

export function resetExam(section = null) {
  if (!window.confirm("Vuoi davvero azzerare le risposte e ricaricare la prova?")) return;
  const targetSection = section || currentSection || "A";
  clearExamStateStorage();
  currentIndex = 0;
  loadExam(targetSection, true, currentBatch);
}

export async function loadNextBatch() {
  currentBatch += 1;
  clearExamStateStorage();
  resetPacingTimer();
  await loadExam(currentSection, true, currentBatch);
}

export async function loadExam(section = "A", clean = false, batch = currentBatch) {
  currentSection = section;
  currentBatch = batch;
  currentIndex = 0;
  highlightSectionBtn(section);

  const qParam = section === "all" ? `?batch=${batch}` : `?section=${section}&batch=${batch}`;
  const res = await fetch(`/api/exams/questions${qParam}`);
  currentQuestions = await res.json();

  const resultsBox = document.getElementById("examResultsBox");
  if (resultsBox) resultsBox.classList.add("hidden");

  if (clean) {
    clearExamStateStorage();
  } else {
    loadExamStateFromStorage();
  }

  const serverNotes = {};
  currentQuestions.forEach((q) => {
    if (q.saved_comment) serverNotes[q.id] = q.saved_comment;
  });
  initExamNotes(serverNotes);

  updateMissingPartsBtnUI(isMissingPartsActive());
  renderExamView();

  startPacingTimer((sec, timeStr) => {
    const tEl = document.getElementById("timeElapsed");
    if (tEl) tEl.innerText = timeStr;
    const ansCount = currentQuestions.filter((q) => getUserAnswer(q.id)).length;
    updatePacingUI(sec, ansCount, currentQuestions.length, currentSection);
  });
}

export function goToQuestion(idx) {
  if (idx < 0 || idx >= currentQuestions.length) return;
  currentIndex = idx;
  renderExamView();
}

export function nextQuestion() {
  if (currentIndex < currentQuestions.length - 1) {
    goToQuestion(currentIndex + 1);
  } else {
    submitExam();
  }
}

export function prevQuestion() {
  if (currentIndex > 0) goToQuestion(currentIndex - 1);
}

export function toggleCurrentNote() {
  toggleNoteState();
}

export function onCharClick(qid, ch) {
  toggleUnknownChar(qid, ch);
  renderExamView();
}

export function setConfidenceLevel(level) {
  const q = currentQuestions[currentIndex];
  if (!q) return;
  setConfidence(q.id, level);
  renderExamView();
}

export function selectExamOption(qid, optKey) {
  setUserAnswer(qid, optKey);
  renderExamView();
}

function renderExamView() {
  renderQuestionRail(currentQuestions, currentIndex);
  renderActiveQuestion(currentQuestions, currentIndex);
  updateProgressUI();
}

function updateProgressUI() {
  const answered = currentQuestions.filter((q) => getUserAnswer(q.id)).length;
  const total = currentQuestions.length;
  const pct = total ? Math.round((answered / total) * 100) : 0;
  const el = document.getElementById("drillAnswerProgress");
  if (el) el.innerText = `${answered} / ${total} (${pct}%)`;
  updatePacingUI(getElapsedSeconds(), answered, total, currentSection);
}

export function submitExam() {
  return submitExamSession(currentQuestions, currentSection);
}

export function switchExamBranch(branch) {
  switchBranchModule(branch, currentQuestions.length, () => loadExam(currentSection));
}

// Wire keyboard listeners for 1-9 confidence, QWAS options, X dont_know, arrows jump
initExamKeybindings(() => currentQuestions, () => currentIndex, {
  setConfidence: setConfidenceLevel,
  selectOption: selectExamOption,
  nextQuestion,
  prevQuestion,
});

// Window Exports
window.loadExam = loadExam;
window.loadNextBatch = loadNextBatch;
window.resetExam = resetExam;
window.confirmResetExamTimer = confirmResetExamTimer;
window.toggleMissingPartsMode = toggleMissingPartsMode;
window.setConfidenceLevel = setConfidenceLevel;
window.onCharClick = onCharClick;
window.selectExamOption = selectExamOption;
window.goToQuestion = goToQuestion;
window.nextQuestion = nextQuestion;
window.prevQuestion = prevQuestion;
window.submitExam = submitExam;
window.switchExamBranch = switchExamBranch;
window.toggleCurrentNote = toggleCurrentNote;
window.getUserAnswer = getUserAnswer;
window.isMissingPartsActive = isMissingPartsActive;
window.getConfidence = getConfidence;
window.getUnknownCharacters = getUnknownChars;
window.getCurrentQuestion = () => currentQuestions[currentIndex];
