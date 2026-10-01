// static/js/modules/anki_web_settings.js — Display & Typography Settings (No Timer Clutter)
// Strictly <= 200 lines invariant.

import { ankiLog } from './anki_logger.js';
import { persistSetting } from './anki_web_persistence.js';

const DEFAULT_FRONT_SIZE = 38;
const DEFAULT_BACK_SIZE = 20;
const DEFAULT_FURIGANA_MODE = 'unstudied'; // 'unstudied' | 'always' | 'hidden'

let _frontSize = DEFAULT_FRONT_SIZE;
let _backSize = DEFAULT_BACK_SIZE;
let _furiganaMode = DEFAULT_FURIGANA_MODE;

const get = id => document.getElementById(id);

export function getFuriganaMode() {
  return _furiganaMode;
}

export function initAnkiSettings() {
  const initS = (typeof window !== 'undefined' && window.__INITIAL_SETTINGS__) ? window.__INITIAL_SETTINGS__ : {};
  const savedFront = localStorage.getItem('anki_front_font_size');
  const savedBack = localStorage.getItem('anki_back_font_size');
  const savedFurigana = localStorage.getItem('anki_furigana_mode');

  _frontSize = savedFront ? (parseInt(savedFront, 10) || DEFAULT_FRONT_SIZE) : (initS.front_font_size || DEFAULT_FRONT_SIZE);
  _backSize = savedBack ? (parseInt(savedBack, 10) || DEFAULT_BACK_SIZE) : (initS.back_font_size || DEFAULT_BACK_SIZE);
  _furiganaMode = savedFurigana && ['unstudied', 'always', 'hidden'].includes(savedFurigana)
    ? savedFurigana
    : (initS.furigana_mode || DEFAULT_FURIGANA_MODE);

  applyFontSizes();
  updateFuriganaButtonsUI();
  setupSettingsListeners();
}

export function toggleSettingsPanel(force) {
  const panel = get('ankiSettingsPanel');
  if (!panel) return;
  const isHidden = panel.classList.contains('hidden');
  const shouldShow = force !== undefined ? force : isHidden;
  panel.classList.toggle('hidden', !shouldShow);
  if (shouldShow) syncSliderInputs();
}

export function setFrontFontSize(size) {
  _frontSize = Math.max(18, Math.min(84, parseInt(size, 10) || DEFAULT_FRONT_SIZE));
  persistSetting('anki_front_font_size', _frontSize);
  applyFontSizes();
  ankiLog('ACTION', 'SETTINGS', 'SET_FRONT_FONT_SIZE', { size: _frontSize });
}

export function setBackFontSize(size) {
  _backSize = Math.max(12, Math.min(48, parseInt(size, 10) || DEFAULT_BACK_SIZE));
  persistSetting('anki_back_font_size', _backSize);
  applyFontSizes();
  ankiLog('ACTION', 'SETTINGS', 'SET_BACK_FONT_SIZE', { size: _backSize });
}

export function setFuriganaMode(mode) {
  if (!['unstudied', 'always', 'hidden'].includes(mode)) return;
  _furiganaMode = mode;
  persistSetting('anki_furigana_mode', mode);
  updateFuriganaButtonsUI();

  if (window.ankiRefreshCurrentCard) {
    window.ankiRefreshCurrentCard();
  }
}

export function resetFontSizes() {
  _frontSize = DEFAULT_FRONT_SIZE;
  _backSize = DEFAULT_BACK_SIZE;
  _furiganaMode = DEFAULT_FURIGANA_MODE;
  persistSetting('anki_front_font_size', _frontSize);
  persistSetting('anki_back_font_size', _backSize);
  persistSetting('anki_furigana_mode', _furiganaMode);
  applyFontSizes();
  updateFuriganaButtonsUI();
  syncSliderInputs();
  if (window.ankiRefreshCurrentCard) {
    window.ankiRefreshCurrentCard();
  }
}

let _appliedFront = -1, _appliedBack = -1;

export function applyFontSizes() {
  if (_frontSize === _appliedFront && _backSize === _appliedBack) return;
  _appliedFront = _frontSize; _appliedBack = _backSize;
  document.documentElement.style.setProperty('--anki-front-font-size', `${_frontSize}px`);
  document.documentElement.style.setProperty('--anki-back-font-size', `${_backSize}px`);

  const frontEl = get('ankiCardFront');
  if (frontEl) frontEl.style.fontSize = `${_frontSize}px`;

  const readingEl = get('ankiCardReading');
  if (readingEl) readingEl.style.fontSize = `${_backSize}px`;

  const meaningEl = get('ankiCardMeaning');
  if (meaningEl) meaningEl.style.fontSize = `${Math.max(14, Math.round(_backSize * 0.88))}px`;

  const lblFront = get('labelFrontFontSize');
  if (lblFront) lblFront.innerText = `${_frontSize}px`;

  const lblBack = get('labelBackFontSize');
  if (lblBack) lblBack.innerText = `${_backSize}px`;
}

function updateFuriganaButtonsUI() {
  const modes = ['unstudied', 'always', 'hidden'];
  const labels = { unstudied: 'Non Noti', always: 'Tutti', hidden: 'Nascosto' };

  const lbl = get('labelFuriganaMode');
  if (lbl) lbl.innerText = labels[_furiganaMode] || 'Non Noti';

  modes.forEach((m) => {
    const btn = get(`btnFurigana${m.charAt(0).toUpperCase() + m.slice(1)}`);
    if (btn) {
      const active = m === _furiganaMode;
      btn.className = active
        ? 'py-1 px-1.5 rounded border border-[#42A5F5] bg-[#42A5F5]/20 text-white font-semibold text-center transition tap-press shadow-sm'
        : 'py-1 px-1.5 rounded border border-[#2C2C2C] bg-[#2A2A2A] text-neutral-400 font-semibold text-center transition tap-press hover:text-white';
    }
  });
}

function syncSliderInputs() {
  const sFront = get('sliderFrontFontSize');
  if (sFront) sFront.value = _frontSize;

  const sBack = get('sliderBackFontSize');
  if (sBack) sBack.value = _backSize;

  const lblFront = get('labelFrontFontSize');
  if (lblFront) lblFront.innerText = `${_frontSize}px`;

  const lblBack = get('labelBackFontSize');
  if (lblBack) lblBack.innerText = `${_backSize}px`;

  updateFuriganaButtonsUI();
}

function setupSettingsListeners() {
  const sFront = get('sliderFrontFontSize');
  if (sFront) sFront.addEventListener('input', (e) => setFrontFontSize(e.target.value));

  const sBack = get('sliderBackFontSize');
  if (sBack) sBack.addEventListener('input', (e) => setBackFontSize(e.target.value));
}
