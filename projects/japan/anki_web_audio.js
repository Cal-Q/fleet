// static/js/modules/anki_web_audio.js — Audio & Speech Synthesis
// Strictly <= 200 lines invariant.

export function playAudio(url) {
  if (url) new Audio(url).play().catch(() => {});
}

export function speakJapanese(text) {
  if (!('speechSynthesis' in window) || !text) return;
  window.speechSynthesis.cancel();
  const utt = new SpeechSynthesisUtterance(text.replace(/<[^>]*>/g, '').trim());
  utt.lang = 'ja-JP';
  utt.rate = 0.95;
  window.speechSynthesis.speak(utt);
}
