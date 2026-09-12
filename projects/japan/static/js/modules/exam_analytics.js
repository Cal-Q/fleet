// static/js/modules/exam_analytics.js — Exam Performance Telemetry & Results Renderer
// Strictly <= 200 lines invariant.

export function renderExamResults(result, spent, currentSection) {
  const resultsBox = document.getElementById("examResultsBox");
  if (!resultsBox) return;
  resultsBox.classList.remove("hidden");
  resultsBox.innerHTML = `
    <div class="p-4 md:p-5 border border-black/10 bg-white space-y-3.5">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-black/10 pb-3">
        <div>
          <div class="text-xl md:text-2xl font-bold font-mono text-[#111111]">Punteggio: ${result.score} / ${result.total} (${result.percentage}%)</div>
          <div class="text-xs md:text-sm text-neutral-500 font-mono">Tempo: ${Math.floor(spent / 60)}m ${spent % 60}s (${result.seconds_per_question}s/q)</div>
        </div>
        <div class="flex items-center gap-2 font-mono text-xs md:text-sm">
          <button onclick=\"window.loadExam('${currentSection}')\" class="px-3.5 py-2 border border-black bg-white hover:bg-black hover:text-white transition tap-press active:scale-95 font-bold">🔄 Riprova</button>
          <button onclick=\"window.switchExamBranch('analytics')\" class="px-3.5 py-2 bg-[#181A1B] text-white hover:bg-black transition tap-press active:scale-95 font-bold">📊 Diagnostica</button>
        </div>
      </div>
      <div class="space-y-2.5 pt-1">
        <h3 class="text-xs md:text-sm font-mono font-bold uppercase tracking-wider text-[#111111]">Analisi Risposte & Distrattori:</h3>
        ${result.details.map(d => `
          <div class="p-3 md:p-3.5 border ${d.is_correct ? "border-[#1E5233]/20 bg-[#EEF7F1]" : "border-[#E63920]/20 bg-[#FDF1EF]"} space-y-2 text-xs md:text-sm">
            <div class="flex items-center justify-between font-mono text-xs md:text-sm">
              <span class="font-bold ${d.is_correct ? "text-[#1E5233]" : "text-[#E63920]"}">${d.is_correct ? "✅ ESATTA" : "❌ ERRATA"}</span>
              <span class="text-neutral-600">Tua: <b>${d.user_answer || "Omessa"}</b> | Corretta: <b>${d.correct_answer}</b></span>
            </div>
            <div class="text-neutral-800 font-sans leading-relaxed text-xs md:text-sm">💡 <b>Analisi:</b> ${d.explanation}</div>
            ${d.user_comment ? `
              <div class="p-2 border border-black/10 bg-white space-y-1 font-sans">
                <span class="text-[11px] font-mono font-bold text-neutral-500 uppercase">📝 La tua nota registrata per revisione:</span>
                <p class="text-neutral-700 italic leading-relaxed">"${d.user_comment}"</p>
              </div>
            ` : ""}
          </div>
        `).join("")}
      </div>
    </div>
  `;
  resultsBox.scrollIntoView({ behavior: "smooth", block: "start" });
}

export async function loadExamAnalytics() {
  try {
    const res = await fetch("/api/exams/analytics");
    const data = await res.json();
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.innerText = val; };
    set("statOverallAccuracy", `${data.overall_accuracy}%`);
    set("statQuestionsCount", `${data.total_questions} quesiti`);
    set("statTotalSessions", `${data.total_sessions} sessioni`);
    set("statAvgPacing", `${data.avg_seconds_per_question}s`);

    const catListEl = document.getElementById("categoryStatsList");
    if (catListEl) {
      catListEl.innerHTML = (!data.category_accuracy || !Object.keys(data.category_accuracy).length)
        ? "<div class=\"text-neutral-400 italic text-center py-2 text-xs md:text-sm\">Nessuna sessione registrata.</div>"
        : Object.entries(data.category_accuracy).map(([cat, info]) => `
          <div class="space-y-1.5 text-xs md:text-sm font-mono">
            <div class="flex justify-between text-xs md:text-sm">
              <span class="truncate max-w-[240px]" title="${cat}">${cat}</span>
              <span class="${info.percentage >= 80 ? "text-[#1E5233]" : (info.percentage >= 60 ? "text-amber-700" : "text-[#E63920]")} font-bold">${info.percentage}% (${info.correct}/${info.total})</span>
            </div>
            <div class="w-full bg-neutral-200 h-1.5"><div class="${info.percentage >= 80 ? "bg-[#1E5233]" : (info.percentage >= 60 ? "bg-amber-600" : "bg-[#E63920]")} h-full" style="width: ${info.percentage}%"></div></div>
          </div>
        `).join("");
    }

    const diagEl = document.getElementById("diagnosticsFocusBox");
    if (diagEl) {
      let h = "";
      if (data.weaknesses?.length) h += `<div class="p-3 border border-[#E63920]/20 bg-[#FDF1EF] text-xs md:text-sm"><b class="text-[#E63920] font-mono">⚠️ Criticità (<65%):</b><ul class="list-disc list-inside mt-1">${data.weaknesses.map(w => `<li>${w.category}: ${w.percentage}%</li>`).join("")}</ul></div>`;
      if (data.strengths?.length) h += `<div class="p-3 border border-[#1E5233]/20 bg-[#EEF7F1] text-xs md:text-sm"><b class="text-[#1E5233] font-mono">✅ Solidi (≥80%):</b><ul class="list-disc list-inside mt-1">${data.strengths.map(s => `<li>${s.category}: ${s.percentage}%</li>`).join("")}</ul></div>`;
      diagEl.innerHTML = h || "<div class=\"text-xs md:text-sm text-neutral-400 font-mono\">Completa almeno 2 quesiti per categoria per sbloccare l'analisi.</div>";
    }
  } catch (err) { console.error("Error loading exam analytics:", err); }
}
