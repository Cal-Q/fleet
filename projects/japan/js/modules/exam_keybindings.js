// static/js/modules/exam_keybindings.js — Exam Keyboard Navigation & Hotkeys
// Strictly <= 200 lines invariant.

export function initExamKeybindings(getQuestions, getIndex, handlers) {
  window.addEventListener("keydown", (e) => {
    const leaf = document.getElementById("leaf_exam_drill");
    if (!leaf || leaf.classList.contains("hidden")) return;
    if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)) return;

    const questions = getQuestions();
    const idx = getIndex();
    const currQ = questions[idx];
    if (!currQ) return;

    const num = parseInt(e.key, 10);
    if (num >= 1 && num <= 9) {
      e.preventDefault();
      handlers.setConfidence(num);
      return;
    }

    const k = e.key.toUpperCase();
    const optMap = { Q: "A", W: "B", A: "C", S: "D" };
    if (optMap[k]) {
      e.preventDefault();
      handlers.selectOption(currQ.id, optMap[k]);
      return;
    }

    if (k === "X") {
      e.preventDefault();
      handlers.selectOption(currQ.id, "DONT_KNOW");
      return;
    }

    if (e.key === "ArrowRight") {
      e.preventDefault();
      handlers.nextQuestion();
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      handlers.prevQuestion();
    }
  });
}
