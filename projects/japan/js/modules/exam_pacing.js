// static/js/modules/exam_pacing.js — MEXT Real-time Pacing Engine & Resilient Timer
// Strictly <= 200 lines invariant.

const STORAGE_KEY_START = "mext_exam_timer_start";
const STORAGE_KEY_ACCUM = "mext_exam_timer_accum";
const STORAGE_KEY_PAUSED = "mext_exam_timer_paused";

let timerInterval = null;
let tickCallback = null;

export function getElapsedSeconds() {
  const accum = parseInt(localStorage.getItem(STORAGE_KEY_ACCUM) || "0", 10);
  const isPaused = localStorage.getItem(STORAGE_KEY_PAUSED) === "true";
  if (isPaused) {
    return accum;
  }
  const startStr = localStorage.getItem(STORAGE_KEY_START);
  if (!startStr) {
    return accum;
  }
  const start = parseInt(startStr, 10);
  const delta = Math.max(0, Math.floor((Date.now() - start) / 1000));
  return accum + delta;
}

export function isTimerPaused() {
  return localStorage.getItem(STORAGE_KEY_PAUSED) === "true";
}

function triggerTick() {
  const elapsedSec = getElapsedSeconds();
  const isPaused = isTimerPaused();
  const timeStr = (isPaused ? "⏸️ " : "") + formatPacingTime(elapsedSec);
  if (typeof tickCallback === "function") {
    tickCallback(elapsedSec, timeStr, isPaused);
  }
}

export function startPacingTimer(onTick) {
  if (onTick) {
    tickCallback = onTick;
  }
  if (!localStorage.getItem(STORAGE_KEY_START)) {
    localStorage.setItem(STORAGE_KEY_START, String(Date.now()));
    localStorage.setItem(STORAGE_KEY_ACCUM, "0");
    localStorage.setItem(STORAGE_KEY_PAUSED, "false");
  }

  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }

  triggerTick();

  const isPaused = localStorage.getItem(STORAGE_KEY_PAUSED) === "true";
  if (!isPaused) {
    timerInterval = setInterval(triggerTick, 1000);
  }
}

export function pausePacingTimer() {
  if (isTimerPaused()) {
    return;
  }
  const currentElapsed = getElapsedSeconds();
  localStorage.setItem(STORAGE_KEY_ACCUM, String(currentElapsed));
  localStorage.setItem(STORAGE_KEY_START, String(Date.now()));
  localStorage.setItem(STORAGE_KEY_PAUSED, "true");
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
  triggerTick();
}

export function resumePacingTimer() {
  if (!isTimerPaused()) {
    return;
  }
  localStorage.setItem(STORAGE_KEY_START, String(Date.now()));
  localStorage.setItem(STORAGE_KEY_PAUSED, "false");
  if (timerInterval) {
    clearInterval(timerInterval);
  }
  timerInterval = setInterval(triggerTick, 1000);
  triggerTick();
}

export function resetPacingTimer() {
  localStorage.setItem(STORAGE_KEY_START, String(Date.now()));
  localStorage.setItem(STORAGE_KEY_ACCUM, "0");
  localStorage.setItem(STORAGE_KEY_PAUSED, "false");
  if (timerInterval) {
    clearInterval(timerInterval);
  }
  timerInterval = setInterval(triggerTick, 1000);
  triggerTick();
}

export function stopPacingTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
}

export function formatPacingTime(sec) {
  const m = String(Math.floor(sec / 60)).padStart(2, "0");
  const s = String(sec % 60).padStart(2, "0");
  return `${m}:${s}`;
}

export function evaluatePacingMetrics(elapsedSec, answeredCount, totalCount, section = "A") {
  if (answeredCount <= 0) {
    return {
      avgSec: 0,
      status: "idle",
      label: "In attesa",
      badgeClass: "text-neutral-400 bg-[#FAF8F5] border-black/10",
    };
  }

  const avgSec = Math.round(elapsedSec / answeredCount);
  const sec = (section || "A").toUpperCase();
  let optLimit = 25;
  let warnLimit = 35;
  if (sec === "B") {
    optLimit = 40;
    warnLimit = 55;
  } else if (sec === "C") {
    optLimit = 120;
    warnLimit = 180;
  }

  if (avgSec <= optLimit) {
    return {
      avgSec,
      status: "optimal",
      label: `${avgSec}s/q • Ottimale (${sec})`,
      badgeClass: "text-[#264332] bg-[#EEF7F1] border-[#264332]/30",
    };
  } else if (avgSec <= warnLimit) {
    return {
      avgSec,
      status: "warning",
      label: `${avgSec}s/q • Attenzione`,
      badgeClass: "text-[#D97706] bg-[#FFFBEB] border-[#D97706]/30",
    };
  }
  return {
    avgSec,
    status: "critical",
    label: `${avgSec}s/q • Lento (Rischio OMR)`,
    badgeClass: "text-[#E63920] bg-[#FDF2F2] border-[#E63920]/30",
  };
}

export function updatePacingUI(elapsedSec, answeredCount, totalCount, section = "A") {
  const metrics = evaluatePacingMetrics(elapsedSec, answeredCount, totalCount, section);
  const pill = document.getElementById("examPacingPill");
  if (pill) {
    pill.className =
      `px-2 py-0.5 border text-xs font-mono font-bold transition-all duration-150 ` +
      metrics.badgeClass;
    pill.innerText = metrics.label;
  }
}
