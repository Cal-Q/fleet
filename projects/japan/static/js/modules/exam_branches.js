// static/js/modules/exam_branches.js — Exam Branch & Section Selector
// Strictly <= 200 lines invariant.

import { loadInterview } from "./interview.js";
import { loadExamAnalytics } from "./exam_analytics.js";

export function highlightSectionBtn(sec) {
  const sections = ["all", "mock", "A", "B", "C"];
  sections.forEach((s) => {
    const b = document.getElementById("btn_sec_" + s);
    if (!b) return;
    const isAct = s === sec;
    const base = "px-2.5 py-1 text-xs font-bold uppercase transition tap-press active:scale-95";
    const actCls = "bg-[#181A1B] text-white shadow-2xs text-center";
    const inactCls = "bg-[#FAF8F5] border border-black/10 hover:border-black text-neutral-600";
    b.className = `${base} ${isAct ? actCls : inactCls}`;
  });
}

export function switchExamBranch(branch, currentCount, onDrillEmpty) {
  const branches = ["drill", "interview", "analytics"];
  branches.forEach((b) => {
    const leaf = document.getElementById("leaf_exam_" + b);
    const btn = document.getElementById("branch_btn_exam_" + b);
    const active = b === branch;
    if (leaf) leaf.classList.toggle("hidden", !active);
    if (btn) {
      const base = "px-2.5 py-1 font-bold transition tap-press active:scale-95";
      const act = "bg-[#181A1B] text-white shadow-2xs";
      const inact = "bg-[#FAF8F5] border border-black/10 hover:border-black text-neutral-600";
      btn.className = `${base} ${active ? act : inact}`;
    }
  });

  if (branch === "interview") {
    loadInterview();
  } else if (branch === "analytics") {
    loadExamAnalytics();
  } else if (branch === "drill" && !currentCount && typeof onDrillEmpty === "function") {
    onDrillEmpty();
  }
}
