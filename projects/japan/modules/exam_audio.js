// static/js/modules/exam_audio.js — Embassy Exam Hall Acoustic Desensitization
let audioCtx = null;
let noiseNode = null;
let gainNode = null;
let tickTimer = null;
let isPlaying = false;
let tickToggle = false;

function getAudioContext() {
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (AudioContextClass) {
      audioCtx = new AudioContextClass();
    }
  }
  if (audioCtx && audioCtx.state === "suspended") {
    audioCtx.resume();
  }
  return audioCtx;
}

function createRoomNoise(ctx) {
  const bufferSize = ctx.sampleRate * 2;
  const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
  const data = buffer.getChannelData(0);
  let lastOut = 0.0;
  for (let i = 0; i < bufferSize; i++) {
    const white = Math.random() * 2 - 1;
    data[i] = (lastOut + 0.02 * white) / 1.02; // Brown/pink room resonance
    lastOut = data[i];
    data[i] *= 3.5;
  }
  const noise = ctx.createBufferSource();
  noise.buffer = buffer;
  noise.loop = true;

  const filter = ctx.createBiquadFilter();
  filter.type = "lowpass";
  filter.frequency.value = 320;

  const gain = ctx.createGain();
  gain.gain.value = 0.04; // Gentle ambient level

  noise.connect(filter);
  filter.connect(gain);
  gain.connect(ctx.destination);
  return { noise, gain };
}

function playClockTick(ctx) {
  if (!isPlaying) return;
  const osc = ctx.createOscillator();
  const tickGain = ctx.createGain();
  const now = ctx.currentTime;

  tickToggle = !tickToggle;
  osc.type = "sine";
  osc.frequency.setValueAtTime(tickToggle ? 1150 : 850, now);

  tickGain.gain.setValueAtTime(0.025, now);
  tickGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.035);

  osc.connect(tickGain);
  tickGain.connect(ctx.destination);
  osc.start(now);
  osc.stop(now + 0.04);
}

export function startAmbientExamAudio() {
  try {
    const ctx = getAudioContext();
    if (!ctx) return false;
    stopAmbientExamAudio();

    const { noise, gain } = createRoomNoise(ctx);
    noiseNode = noise;
    gainNode = gain;
    noiseNode.start(0);
    isPlaying = true;

    tickTimer = setInterval(() => {
      if (isPlaying && audioCtx) playClockTick(audioCtx);
    }, 1000);

    updateAudioUI(true);
    return true;
  } catch (e) {
    console.warn("Ambient audio error:", e);
    return false;
  }
}

export function stopAmbientExamAudio() {
  isPlaying = false;
  if (tickTimer) {
    clearInterval(tickTimer);
    tickTimer = null;
  }
  if (noiseNode) {
    try { noiseNode.stop(); noiseNode.disconnect(); } catch (_) {}
    noiseNode = null;
  }
  updateAudioUI(false);
  return false;
}

export function toggleAmbientExamAudio() {
  return isPlaying ? stopAmbientExamAudio() : startAmbientExamAudio();
}

function updateAudioUI(active) {
  const statusEl = document.getElementById("ambientSoundStatus");
  const btnEl = document.getElementById("ambientSoundToggle");
  if (statusEl) {
    statusEl.textContent = active ? "ON (Attivo)" : "OFF";
    statusEl.className = active ? "text-[#264332] font-bold" : "text-neutral-400";
  }
  if (btnEl) {
    if (active) {
      btnEl.classList.add("border-[#264332]/40", "bg-[#EEF7F1]");
    } else {
      btnEl.classList.remove("border-[#264332]/40", "bg-[#EEF7F1]");
    }
  }
}
