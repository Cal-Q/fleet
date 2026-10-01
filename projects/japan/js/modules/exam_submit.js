// static/js/modules/exam_submit.js — Exam Submission & Persistence Dispatcher
// Strictly <= 200 lines invariant.

import { renderExamResults, loadExamAnalytics } from "./exam_analytics.js";
import { getAllUserComments } from "./exam_notes.js";
import { stopPacingTimer, resetPacingTimer, getElapsedSeconds } from "./exam_pacing.js";
import {
  getUserAnswer,
  getAllAnswers,
  getAllConfidence,
  getAllUnknownChars,
  clearExamStateStorage,
} from "./exam_state.js";

export async function submitExamSession(currentQuestions, currentSection) {
  const answered = currentQuestions.filter((q) => getUserAnswer(q.id)).length;
  const total = currentQuestions.length;
  if (answered < total) {
    const remaining = total - answered;
    const msg = `Ci sono ancora ${remaining} quesiti senza risposta.\nVuoi consegnare comunque?`;
    if (!window.confirm(msg)) {
      return;
    }
  }

  stopPacingTimer();
  const spent = getElapsedSeconds();
  const answers = getAllAnswers();
  const confidence_levels = getAllConfidence();
  const unknown_characters = getAllUnknownChars();
  const comments = getAllUserComments();

  const res = await fetch("/api/exams/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      answers,
      comments,
      confidence_levels,
      unknown_characters,
      time_spent_seconds: spent,
    }),
  });
  const result = await res.json();

  clearExamStateStorage();
  resetPacingTimer();
  loadExamAnalytics();

  if (typeof window.markRoutineSlotDone === "function") {
    window.markRoutineSlotDone("slot1");
  }

  const single = document.getElementById("examSingleContainer");
  if (single) {
    single.innerHTML = "";
  }
  renderExamResults(result, spent, currentSection);
}
