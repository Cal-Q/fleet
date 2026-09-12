// static/js/modules/exam_notes.js — Persistent Question Notes & Auto-Save
// Strictly <= 200 lines invariant.

let userComments = {};
const saveTimers = {};

export function initExamNotes(initialNotes = {}) {
  try {
    const local = JSON.parse(localStorage.getItem("mext_exam_notes") || "{}");
    Object.keys(local).forEach(k => {
      if (typeof local[k] === 'string' && (local[k].includes('Commento aggiornato') || local[k].includes('Dubbio sul significato'))) {
        delete local[k];
      }
    });
    localStorage.setItem("mext_exam_notes", JSON.stringify(local));
    userComments = { ...local, ...initialNotes };
  } catch (e) {
    userComments = { ...initialNotes };
  }
}

export function getUserComment(qid) {
  return userComments[qid] || "";
}

export function getAllUserComments() {
  return { ...userComments };
}

export function saveQuestionNote(qid) {
  const el = document.getElementById(`note_${qid}`);
  const statusEl = document.getElementById(`note_status_${qid}`);
  if (!el) return;

  const text = el.value;
  userComments[qid] = text;

  try {
    localStorage.setItem("mext_exam_notes", JSON.stringify(userComments));
  } catch (e) {}

  if (statusEl) {
    statusEl.innerText = "Salvataggio in corso...";
    statusEl.className = "text-[11px] font-mono text-amber-600";
  }

  if (saveTimers[qid]) clearTimeout(saveTimers[qid]);
  saveTimers[qid] = setTimeout(async () => {
    try {
      const currentAns = (typeof window.getUserAnswer === "function") ? window.getUserAnswer(qid) : "";
      await fetch("/api/exams/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question_id: qid, comment: text, answer: currentAns })
      });
      if (statusEl) {
        statusEl.innerText = "💾 Salvato per revisione";
        statusEl.className = "text-[11px] font-mono text-[#1E5233] font-bold";
      }
    } catch (err) {
      if (statusEl) {
        statusEl.innerText = "Salvataggio locale (offline)";
        statusEl.className = "text-[11px] font-mono text-neutral-500";
      }
    }
  }, 600);
}
