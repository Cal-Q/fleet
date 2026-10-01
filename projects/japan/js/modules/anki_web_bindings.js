// static/js/modules/anki_web_bindings.js
// Global Window API Registration for AnkiDroid Web (<= 200 lines, <= 100 cols)

export function registerWindowBindings(bindings) {
  Object.assign(window, {
    ankiShowDeckList: bindings.loadDecksList,
    ankiReloadDecks: bindings.hardReset,
    ankiHardReset: bindings.hardReset,
    ankiForceSyncDecks: bindings.forceSyncDecks,
    ankiResetCardTimer: bindings.resetCurrentCardTimer,
    ankiOpenDeckOverview: bindings.openDeckOverview,
    ankiLaunchStudySession: bindings.launchStudySession,
    ankiToggleDeckCollapse: bindings.toggleDeckCollapse,
    ankiToggleAllCollapse: bindings.toggleAllDecksCollapse,
    ankiFlipCard: bindings.flipCard,
    ankiAnswerCard: bindings.answerCard,
    ankiTriggerSwipe: bindings.triggerProgrammaticSwipe,
    ankiUndo: bindings.undoReview,
    ankiUndoReview: bindings.undoReview,
    ankiSpeak: bindings.speakJapanese,
    ankiPlayAudio: bindings.playAudio,
    ankiToggleSettings: bindings.handleToggleSettings,
    ankiResetSettings: bindings.resetFontSizes,
    ankiSetFuriganaMode: bindings.setFuriganaMode,
    ankiSetFrontFontSize: bindings.setFrontFontSize,
    ankiSetBackFontSize: bindings.setBackFontSize,
    ankiSetTimerDuration: bindings.setTimerDuration,
    ankiApplyTimerToAllDecks: bindings.applyTimerToAllDecks,
    ankiRefreshCurrentCard: bindings.refreshCurrentCardView,
    ankiGetCurrentCard: bindings.getCurrentCard,
    ankiOpenDeckSettings: bindings.openDeckSettings,
    ankiRenderTestCard: bindings.renderTestCard,
    ankiRenderSessionFinished: bindings.renderSessionFinished,
    ankiSetSessionTarget: bindings.setSessionTargetMin,
    ankiStartBreak: bindings.startMicroBreak,
    ankiStopBreak: bindings.stopMicroBreak,
    ankiDismissFatigue: bindings.hideFatigueModal,
    ankiToggleFatigueDebug: bindings.toggleFatigueDebug,
    ankiAltRule: bindings.triggerAltRuleAction
  });
}
