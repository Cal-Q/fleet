// static/js/modules/exams.js — MEXT Exam Drill Engine & Analytics
// Strictly <= 200 lines invariant.

let currentQuestions = [];
let examStartTime = null;
let timerInterval = null;

export async function loadExam(section = 'all') {
  const url = (section === 'all') ? '/api/exams/questions' : `/api/exams/questions?section=${section}`;
  const res = await fetch(url);
  currentQuestions = await res.json();

  const container = document.getElementById('examContainer');
  const resultsBox = document.getElementById('examResultsBox');
  if (!container) return;
  container.innerHTML = '';
  if (resultsBox) resultsBox.classList.add('hidden');

  currentQuestions.forEach((q, idx) => {
    const card = document.createElement('div');
    card.className = 'p-5 border border-black/10 bg-white space-y-3';
    card.innerHTML = `
      <div class="flex items-center justify-between text-xs text-neutral-500 border-b border-black/5 pb-2 font-mono">
        <span class="font-bold text-[#E63920]">Q.${String(idx + 1).padStart(2, '0')} • SEZIONE ${q.section} (${q.level || 'N/A'})</span>
        <span class="text-neutral-600">${q.category || 'Generale'}</span>
      </div>
      <div class="jp-font text-base text-[#111111] font-medium whitespace-pre-line leading-relaxed">${q.question}</div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1 font-mono text-xs">
        ${['A', 'B', 'C', 'D'].filter(k => q.options[k]).map(k => `
          <label class="flex items-center gap-3 p-3 border border-black/10 bg-[#FAF9F6] hover:bg-white hover:border-black cursor-pointer transition tap-press">
            <input type="radio" name="question_${q.id}" value="${k}" class="accent-[#E63920]">
            <span class="font-bold text-neutral-500">${k}.</span>
            <span class="jp-font text-[#111111] font-medium">${q.options[k]}</span>
          </label>
        `).join('')}
      </div>
    `;
    container.appendChild(card);
  });

  // Start timer
  examStartTime = Date.now();
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    const sec = Math.floor((Date.now() - examStartTime) / 1000);
    const m = String(Math.floor(sec / 60)).padStart(2, '0');
    const s = String(sec % 60).padStart(2, '0');
    const tEl = document.getElementById('timeElapsed');
    if (tEl) tEl.innerText = `${m}:${s}`;
  }, 1000);
}

export async function submitExam() {
  if (timerInterval) clearInterval(timerInterval);
  const spent = examStartTime ? Math.floor((Date.now() - examStartTime) / 1000) : 0;
  const answers = {};

  currentQuestions.forEach(q => {
    const checked = document.querySelector(`input[name="question_${q.id}"]:checked`);
    if (checked) answers[q.id] = checked.value;
  });

  const res = await fetch('/api/exams/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answers, time_spent_seconds: spent })
  });
  const result = await res.json();
  loadExamAnalytics();
  if (typeof window.markRoutineSlotDone === 'function') window.markRoutineSlotDone('slot4');

  const resultsBox = document.getElementById('examResultsBox');
  if (!resultsBox) return;
  resultsBox.classList.remove('hidden');
  resultsBox.innerHTML = `
    <div class="p-4 border border-black/10 bg-white space-y-3">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-black/10 pb-3">
        <div>
          <div class="text-xl font-bold font-mono text-[#111111]">Punteggio: ${result.score} / ${result.total} (${result.percentage}%)</div>
          <div class="text-xs text-neutral-500 font-mono">Tempo: ${Math.floor(spent / 60)}m ${spent % 60}s (${result.seconds_per_question}s/q)</div>
        </div>
        <div class="text-xs space-y-0.5 text-right font-mono">
          ${Object.entries(result.breakdown).map(([sec, d]) => `<div>Sez. ${sec}: <strong class="text-[#1E5233]">${d.correct}</strong>/${d.total}</div>`).join('')}
        </div>
      </div>
      <div class="space-y-2 pt-1">
        <h3 class="text-xs font-mono font-bold uppercase tracking-wider text-[#111111]">Analisi Risposte & Distrattori:</h3>
        ${result.details.map(d => `
          <div class="p-2.5 border ${d.is_correct ? 'border-[#1E5233]/20 bg-[#EEF7F1]' : 'border-[#E63920]/20 bg-[#FDF1EF]'} space-y-1 text-xs">
            <div class="flex items-center justify-between font-mono text-[11px]">
              <span class="font-bold ${d.is_correct ? 'text-[#1E5233]' : 'text-[#E63920]'}">${d.is_correct ? '✅ ESATTA' : '❌ ERRATA'}</span>
              <span class="text-neutral-600">Tua: <b>${d.user_answer || '—'}</b> | Corretta: <b>${d.correct_answer}</b></span>
            </div>
            <div class="text-neutral-800 font-sans">💡 <b>Analisi:</b> ${d.explanation}</div>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

export async function loadExamAnalytics() {
  try {
    const res = await fetch('/api/exams/analytics');
    const data = await res.json();
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.innerText = val; };
    set('statOverallAccuracy', `${data.overall_accuracy}%`);
    set('statQuestionsCount', `${data.total_questions} quesiti svolti`);
    set('statTotalSessions', `${data.total_sessions} sessioni`);
    set('statTotalTime', `${data.total_time_minutes} min studio`);
    set('statAvgPacing', `${data.avg_seconds_per_question}s`);

    const catListEl = document.getElementById('categoryStatsList');
    if (catListEl) {
      if (!data.category_accuracy || !Object.keys(data.category_accuracy).length) {
        catListEl.innerHTML = '<div class="text-neutral-400 italic text-center py-2 text-xs">Nessuna sessione registrata.</div>';
      } else {
        catListEl.innerHTML = Object.entries(data.category_accuracy).map(([cat, info]) => `
          <div class="space-y-1 text-xs font-mono">
            <div class="flex justify-between text-[11px]">
              <span class="truncate max-w-[200px]" title="${cat}">${cat}</span>
              <span class="${info.percentage >= 80 ? 'text-[#1E5233]' : (info.percentage >= 60 ? 'text-amber-700' : 'text-[#E63920]')} font-bold">${info.percentage}% (${info.correct}/${info.total})</span>
            </div>
            <div class="w-full bg-neutral-200 h-1"><div class="${info.percentage >= 80 ? 'bg-[#1E5233]' : (info.percentage >= 60 ? 'bg-amber-600' : 'bg-[#E63920]')} h-full" style="width: ${info.percentage}%"></div></div>
          </div>
        `).join('');
      }
    }

    const diagEl = document.getElementById('diagnosticsFocusBox');
    if (diagEl) {
      let h = '';
      if (data.weaknesses?.length) h += `<div class="p-2 border border-[#E63920]/20 bg-[#FDF1EF] text-xs"><b class="text-[#E63920] font-mono">⚠️ Criticità (<65%):</b><ul class="list-disc list-inside mt-1">${data.weaknesses.map(w => `<li>${w.category}: ${w.percentage}%</li>`).join('')}</ul></div>`;
      if (data.strengths?.length) h += `<div class="p-2 border border-[#1E5233]/20 bg-[#EEF7F1] text-xs"><b class="text-[#1E5233] font-mono">✅ Solidi (≥80%):</b><ul class="list-disc list-inside mt-1">${data.strengths.map(s => `<li>${s.category}: ${s.percentage}%</li>`).join('')}</ul></div>`;
      diagEl.innerHTML = h || '<div class="text-xs text-neutral-400 font-mono">Completa almeno 2 quesiti per categoria per attivare i consigli.</div>';
    }
  } catch (err) { console.error('Error loading exam analytics:', err); }
}

export function switchExamBranch(branch) {
  const isDrill = branch === 'drill';
  const leafDrill = document.getElementById('leaf_exam_drill');
  const leafAnalytics = document.getElementById('leaf_exam_analytics');
  const btnDrill = document.getElementById('branch_btn_exam_drill');
  const btnAnalytics = document.getElementById('branch_btn_exam_analytics');
  if (leafDrill) leafDrill.classList.toggle('hidden', !isDrill);
  if (leafAnalytics) leafAnalytics.classList.toggle('hidden', isDrill);
  if (btnDrill) {
    btnDrill.classList.toggle('bg-white', isDrill);
    btnDrill.classList.toggle('opacity-70', !isDrill);
  }
  if (btnAnalytics) {
    btnAnalytics.classList.toggle('bg-white', !isDrill);
    btnAnalytics.classList.toggle('opacity-70', isDrill);
  }
}

