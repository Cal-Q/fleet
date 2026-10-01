// static/js/modules/navigation.js — Tab Switching & Countdown Ticker
// Strictly <= 200 lines invariant.

export const TAB_IDS = ['study', 'dossier', 'bunki', 'exams', 'interview', 'unis', 'strategy', 'research'];

export function initCountdown() {
  // MEXT 2027 application deadline: 5 Febbraio 2027, 08:00 AM Italian time (UTC+1)
  const targetTime = new Date('2027-02-05T08:00:00+01:00').getTime();
  const daysEl = document.getElementById('countDays');
  const hoursEl = document.getElementById('countHours');
  const minsEl = document.getElementById('countMins');
  const secsEl = document.getElementById('countSecs');

  function tick() {
    const now = Date.now();
    const diff = Math.max(0, targetTime - now);
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff / (1000 * 60 * 60)) % 24);
    const mins = Math.floor((diff / (1000 * 60)) % 60);
    const secs = Math.floor((diff / 1000) % 60);

    if (daysEl) daysEl.innerText = String(days).padStart(3, '0');
    if (hoursEl) hoursEl.innerText = String(hours).padStart(2, '0');
    if (minsEl) minsEl.innerText = String(mins).padStart(2, '0');
    if (secsEl) secsEl.innerText = String(secs).padStart(2, '0');
    const cDaysEl = document.getElementById('countdownDays');
    if (cDaysEl) cDaysEl.innerText = `${days}d`;
  }

  tick();
  setInterval(tick, 1000);
}

export function switchTab(tabId) {
  TAB_IDS.forEach(id => {
    const sec = document.getElementById('section-' + id);
    const tab = document.getElementById('tab-' + id);
    if (sec && tab) {
      if (id === tabId) {
        sec.classList.remove('hidden');
        tab.classList.add('active-dock-tab');
        tab.classList.remove('border-transparent', 'text-neutral-500');
        tab.classList.add('border-black', 'text-[#111111]');
      } else {
        sec.classList.add('hidden');
        tab.classList.remove('active-dock-tab');
        tab.classList.remove('border-black', 'text-[#111111]');
        tab.classList.add('border-transparent', 'text-neutral-500');
      }
    }
  });

  window.dispatchEvent(new CustomEvent('tab-switched', { detail: { tabId } }));
}

export function initKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    if (['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName)) return;
    const key = e.key;
    if (key >= '1' && key <= '8') {
      const idx = parseInt(key, 10) - 1;
      if (TAB_IDS[idx]) {
        switchTab(TAB_IDS[idx]);
      }
    }
  });
}
