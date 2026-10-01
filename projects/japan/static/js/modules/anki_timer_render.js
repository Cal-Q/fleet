// static/js/modules/anki_timer_render.js
// Timer DOM Rendering & Visual State Updates (<= 200 lines, <= 100 cols)

const get = (id) => document.getElementById(id);

let _lastRemainSec = -1;
let _lastPhase = '';

export function resetTimerRenderState() {
  _lastRemainSec = -1;
  _lastPhase = '';
}

export function showTimerBar() {
  get('ankiTimerContainer')?.classList.remove('hidden');
}

export function formatTime(sec) {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  if (m > 0) {
    return `${m}:${String(s).padStart(2, '0')}`;
  }
  return `${s}s`;
}

export function bounceTimerText() {
  const textEl = get('ankiTimerText');
  if (textEl) {
    textEl.style.transform = 'scale(1.25)';
    setTimeout(() => {
      if (textEl) textEl.style.transform = 'scale(1)';
    }, 150);
  }
}

export function updateTimerUI(durationSec, elapsedMs) {
  const progressEl = get('ankiTimerProgress');
  const textEl = get('ankiTimerText');
  const iconEl = get('ankiTimerIcon');
  if (!progressEl || !textEl) return;

  if (durationSec <= 0) {
    const s = Math.floor(elapsedMs / 1000);
    if (s !== _lastRemainSec) {
      _lastRemainSec = s;
      textEl.innerText = formatTime(s);
      textEl.className = 'font-bold text-[#42A5F5] w-12 text-right flex-shrink-0 text-[11px]';
      if (iconEl) iconEl.innerText = '⏱️';
      progressEl.style.transition = 'none';
      progressEl.style.transform = 'scaleX(1)';
      progressEl.className =
        'h-full w-full rounded-full bg-[#42A5F5]/40 origin-left animate-pulse';
    }
    return;
  }

  const totalMs = durationSec * 1000;
  const remainMs = Math.max(0, totalMs - elapsedMs);
  const remainSec = Math.ceil(remainMs / 1000);
  const fraction = Math.max(0, Math.min(1, remainMs / totalMs));

  if (elapsedMs > 0) {
    progressEl.style.transition = 'transform 0.1s linear';
  }
  progressEl.style.transform = `scaleX(${fraction})`;

  const pct = fraction * 100;
  const phase = pct > 50 ? 'good' : (pct > 25 ? 'warn' : 'danger');

  if (remainSec !== _lastRemainSec || phase !== _lastPhase) {
    _lastRemainSec = remainSec;
    _lastPhase = phase;
    textEl.innerText = `${remainSec}s`;
    if (iconEl) iconEl.innerText = '⏳';
    const bgCol = phase === 'good' ? 'bg-[#66BB6A]' : (
      phase === 'warn' ? 'bg-[#FFA726]' : 'bg-[#EF5350]'
    );
    progressEl.className = `h-full w-full rounded-full ${bgCol} origin-left`;
    const textCol = phase === 'good' ? 'text-white' : (
      phase === 'warn' ? 'text-[#FFA726]' : 'text-[#EF5350]'
    );
    textEl.className =
      `font-bold ${textCol} w-12 text-right flex-shrink-0 text-[11px]`;
  }
}

export function onTimerExpiredUI() {
  const textEl = get('ankiTimerText');
  if (textEl) {
    textEl.innerText = '0s';
    textEl.classList.add('animate-pulse', 'text-[#EF5350]');
  }
}

export function updateTimerSettingsUI(durationSec, currentDeckName) {
  const slider = get('sliderTimerDuration');
  const label = get('labelTimerDuration');
  const deckLabel = get('labelTimerDeckTarget');
  if (slider) slider.value = durationSec;
  if (label) {
    label.innerText = durationSec > 0 ? `${durationSec}s` : 'Cronometro (Libero)';
    label.className = durationSec > 0 ? 'font-bold text-[#FFA726]' : 'font-bold text-[#42A5F5]';
  }
  if (deckLabel) {
    const dName = currentDeckName ? currentDeckName.split('::').pop() : 'Tutti i Mazzi';
    deckLabel.innerText = `Mazzo: ${dName}`;
  }
}
