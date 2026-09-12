// static/js/modules/interview.js — Embassy Mock Interview & Keigo Speech Synthesis
// Strictly <= 200 lines invariant.

export async function loadInterview() {
  try {
    const res = await fetch('/api/interview/questions');
    const questions = await res.json();
    const container = document.getElementById('interviewContainer');
    if (!container) return;
    container.innerHTML = '';

    questions.forEach((q, idx) => {
      const card = document.createElement('div');
      card.className = 'p-5 border border-black/10 bg-white space-y-3';
      card.innerHTML = `
        <div class="flex items-center justify-between border-b border-black/5 pb-2">
          <span class="text-[10px] font-mono font-bold text-[#E63920] uppercase tracking-wider">${q.category}</span>
          <button onclick="window.speakJapanese('${encodeURIComponent(q.question_ja)}')" class="text-[11px] font-mono border border-black/20 px-2.5 py-1 bg-[#FAF9F6] hover:bg-white hover:border-black transition flex items-center gap-1 tap-press">
            <span>🔊</span> <span>Ascolta Pronuncia</span>
          </button>
        </div>
        <div class="jp-font text-base text-[#111111] font-medium leading-relaxed">${q.question_ja}</div>
        <p class="text-xs text-neutral-600 italic font-serif">🇮🇹 ${q.question_it}</p>
        
        <div class="pt-2">
          <button onclick="window.toggleInlineModel('model_${q.id}')" class="text-xs font-mono font-bold border border-black px-3 py-1.5 hover:bg-black hover:text-white transition tap-press">
            Mostra Punti Chiave & Risposta Modello (敬語) ↓
          </button>
          <div id="model_${q.id}" class="disclosure-drawer mt-3">
            <div class="p-4 bg-[#FAF9F6] border border-black/10 space-y-3 text-xs">
              <div>
                <strong class="text-[#92580A] font-mono uppercase text-[11px]">Punti Metodologici Chiave:</strong>
                <ul class="list-disc list-inside text-neutral-700 mt-1 space-y-0.5 font-sans">
                  ${q.key_points.map(pt => `<li>${pt}</li>`).join('')}
                </ul>
              </div>
              <div>
                <strong class="text-[#1E5233] font-mono uppercase text-[11px]">Risposta Modello Ufficiale (Sonkeigo / Kenjougo):</strong>
                <p class="jp-font text-[#111111] bg-white p-3 border border-black/10 mt-1 leading-relaxed">「${q.model_answer_ja}」</p>
              </div>
            </div>
          </div>
        </div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    console.error('Error loading interview questions:', err);
  }
}

export function speakJapanese(encodedText) {
  const text = decodeURIComponent(encodedText);
  if ('speechSynthesis' in window) {
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = 'ja-JP';
    utter.rate = 0.92;
    window.speechSynthesis.speak(utter);
    if (typeof window.markRoutineSlotDone === 'function') window.markRoutineSlotDone('slot3');
  } else {
    alert('Sintesi vocale ja-JP non supportata dal browser in uso.');
  }
}

export function toggleInlineModel(id) {
  const el = document.getElementById(id);
  if (el) {
    el.classList.toggle('open');
    if (typeof window.markRoutineSlotDone === 'function') window.markRoutineSlotDone('slot3');
  }
}
