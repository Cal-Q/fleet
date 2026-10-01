// static/js/modules/anki_web_ui.js — Controller & Event Coordinator (<= 200 lines, <= 100 cols)
import { flushReviewOutbox } from './anki_web_db.js';
import {
  loadDecksListImpl, openDeckOverview, toggleDeckCollapse, toggleAllDecksCollapse,
  forceSyncDecks
} from './anki_web_decks.js';
import { speakJapanese, playAudio } from './anki_web_audio.js';
import {
  initCardTimer, setTimerDuration, applyTimerToAllDecks,
  setCurrentDeck as setTimerDeck, getTimerRemainingRatio
} from './anki_web_timer.js';
import {
  initSessionTimer, pauseSessionTimer, setSessionTargetMin
} from './anki_web_session_timer.js';
import {
  hideFatigueModal, startMicroBreak, stopMicroBreak, toggleFatigueDebug
} from './anki_web_fatigue.js';
import {
  initCardSwipe, initCardKeybindings, animateCardEntrance, resetCardPosition,
  triggerProgrammaticSwipe
} from './anki_web_gestures.js';
import {
  initAnkiSettings, setFrontFontSize, setBackFontSize, setFuriganaMode,
  resetFontSizes, toggleSettingsPanel
} from './anki_web_settings.js';
import { initSettingsSync } from './anki_web_persistence.js';
import { applyUpdate } from './anki_web_updater.js';
import { ankiLog } from './anki_logger.js';
import {
  setCurrentDeck, updateCardElements, renderSessionFinished, refreshCurrentCardView
} from './anki_web_study.js';
import { clearCooldownTimer } from './anki_web_queue.js';
import {
  getCurrentCard, isCardFlipped, isAnswering, hasReviewHistory,
  resetCurrentCardTimer, triggerAltRuleAction, flipCard, unflipAndResetTimer,
  undoReview, launchStudySession, answerCard
} from './anki_study_runner.js';
import { registerWindowBindings } from './anki_web_bindings.js';

const get = (id) => document.getElementById(id);

export async function initAnkiWeb() {
  ankiLog('ACTION', 'SYSTEM', 'INIT_ANKI_WEB', {});
  try {
    initAnkiSettings();
    initSessionTimer();
    initCardTimer();
  } catch {}
  setupGestures();
  initSettingsSync(() => {
    try {
      initAnkiSettings();
      initSessionTimer();
      initCardTimer();
    } catch {}
  }).catch(() => {});
  await loadDecksList();
}

export async function loadDecksList() {
  pauseSessionTimer();
  clearCooldownTimer();
  try {
    await flushReviewOutbox();
  } catch {}
  await loadDecksListImpl();
}

function handleCardTap() {
  if (!isCardFlipped()) flipCard();
}

function setupGestures() {
  const cardEl = get('ankiCardContainer');
  initCardSwipe(
    cardEl,
    get('ankiBadgeWrong'),
    get('ankiBadgeCorrect'),
    get('ankiBadgeUndo'),
    () => isCardFlipped() && !isAnswering(),
    () => hasReviewHistory() && !isAnswering(),
    (g) => answerCard(g, loadDecksList),
    handleCardTap,
    () => undoReview(),
    () => resetCurrentCardTimer(),
    () => triggerAltRuleAction(loadDecksList),
    () => getTimerRemainingRatio()
  );
  initCardKeybindings(
    () => isCardFlipped() && !isAnswering(),
    (g) => answerCard(g, loadDecksList),
    handleCardTap,
    () => undoReview(),
    () => resetCurrentCardTimer(),
    () => triggerAltRuleAction(loadDecksList),
    () => getTimerRemainingRatio()
  );
}

function handleToggleSettings(f) {
  const c = getCurrentCard();
  if (c) setCurrentDeck(c.did || c.deck_id, c.deck_name);
  toggleSettingsPanel(f);
}

export async function hardReset() {
  ankiLog('ACTION', 'SYSTEM', 'HARD_RESET', {});
  await forceSyncDecks();
}

registerWindowBindings({
  loadDecksList,
  hardReset,
  forceSyncDecks,
  resetCurrentCardTimer,
  openDeckOverview,
  launchStudySession: () => launchStudySession(loadDecksList),
  toggleDeckCollapse,
  toggleAllDecksCollapse,
  flipCard,
  answerCard: (g) => answerCard(g, loadDecksList),
  triggerProgrammaticSwipe,
  undoReview,
  speakJapanese,
  playAudio,
  handleToggleSettings,
  resetFontSizes,
  setFuriganaMode,
  setFrontFontSize,
  setBackFontSize,
  setTimerDuration,
  applyTimerToAllDecks,
  refreshCurrentCardView,
  getCurrentCard,
  openDeckSettings: (did, name) => {
    setCurrentDeck(did, name);
    setTimerDeck(did, name);
    if (window.ankiOpenCardTimerModal) window.ankiOpenCardTimerModal(did, name);
  },
  renderTestCard: (c, f) => updateCardElements(c, f),
  renderSessionFinished,
  setSessionTargetMin,
  startMicroBreak,
  stopMicroBreak,
  hideFatigueModal,
  toggleFatigueDebug,
  triggerAltRuleAction: () => triggerAltRuleAction(loadDecksList)
});

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAnkiWeb);
} else {
  initAnkiWeb();
}
