// static/js/modules/exam_pacing.js — MEXT Real-time Pacing Engine & Tactical Timer
// Strictly <= 200 lines invariant.

let examStartTime = null;
let timerInterval = null;

export function startPacingTimer(onTick) {
  stopPacingTimer();
  examStartTime = Date.now();
  timerInterval = setInterval(() => {
    const elapsedSec = getElapsedSeconds();
    if (typeof onTick === "function") {
      onTick(elapsedSec, formatPacingTime(elapsedSec));
    }
  }, 1000);
}

export function stopPacingTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
}

export function getElapsedSeconds() {
  if (!examStartTime) return 0;
  return Math.floor((Date.now() - examStartTime) / 1000);
}

export function formatPacingTime(sec) {
  const m = String(Math.floor(sec / 60)).padStart(2, "0");
  const s = String(sec % 60).padStart(2, "0");
  return `${m}:${s}`;
}

export function evaluatePacingMetrics(elapsedSec, answeredCount, totalCount) {
  if (answeredCount <= 0) {
    return {
      avgSec: 0,
      status: "idle",
      label: "In attesa",
      badgeClass: "text-neutral-400 bg-[#FAF8F5] border-black/10"
    };
  }

  const avgSec = Math.round(elapsedSec / answeredCount);
  // Target: <= 30s per question is optimal for completing 100 questions within 60 min
  if (avgSec <= 30) {
    return {
      avgSec,
      status: "optimal",
      label: `${avgSec}s/q • Ottimale`,
      badgeClass: "text-[#264332] bg-[#EEF7F1] border-[#264332]/30"
    };
  } else if (avgSec <= 45) {
    return {
      avgSec,
      status: "warning",
      label: `${avgSec}s/q • Attenzione`,
      badgeClass: "text-[#D97706] bg-[#FFFBEB] border-[#D97706]/30"
    };
  } else {
    return {
      avgSec,
      status: "critical",
      label: `${avgSec}s/q • Lento (Rischio OMR)`,
      badgeClass: "text-[#E63920] bg-[#FDF2F2] border-[#E63920]/30"
    };
  }
}

export function updatePacingUI(elapsedSec, answeredCount, totalCount) {
  const metrics = evaluatePacingMetrics(elapsedSec, answeredCount, totalCount);
  const pill = document.getElementById("examPacingPill");
  if (pill) {
    pill.className = `px-2 py-0.5 border text-xs font-mono font-bold transition-all duration-150 ${metrics.badgeClass}`;
    pill.innerText = metrics.label;
  }
}
