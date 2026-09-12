// static/js/main.js — Main Application Orchestration
// Strictly <= 200 lines invariant.

import { initCountdown } from './modules/navigation.js';
import { initDock, setActiveStage, getActiveStage } from './modules/dock.js';
import { initViewport } from './modules/viewport.js';
import { loadStudyStatus, searchManualVocab, switchStudyBranch, syncBatchGroup, toggleDrawer } from './modules/study.js';
import { loadCareer, loadDossierStatus, updateDocStatus, switchDossierBranch } from './modules/dossier.js';
import { loadBunkiProfile, reviewLeechAction, verifySlot1WithAnkiWeb, syncSlot1UI } from './modules/bunki.js';
import { loadExam, loadExamAnalytics, submitExam, switchExamBranch } from './modules/exams.js';
import { loadInterview, speakJapanese, toggleInlineModel } from './modules/interview.js';
import { loadResearchDossiers, previewDossier } from './modules/research.js';
import { initDailyRoutine, launchRoutineSlot, markRoutineSlotDone, unmarkRoutineSlot, toggleRoutineSlot, updateRoutineProgress } from './modules/routine.js';
import { initDragScroll } from './modules/drag_scroll.js';

// Sinoira Gang Navigation globals
window.setActiveStage = setActiveStage;
window.getActiveStage = getActiveStage;

// Backward-compatible bridge for legacy switchTab calls
window.switchTab = (tabId) => {
  const stageMap = {
    routine: 'routine',
    study: 'study',
    bunki: 'bunki',
    exams: 'exams',
    dossier: 'dossier',
    strategy: 'dossier',
    unis: 'dossier',
    interview: 'exams',
    research: 'dossier'
  };
  const target = stageMap[tabId] || 'routine';
  setActiveStage(target, true);

  if (['strategy', 'unis'].includes(tabId) && typeof window.switchDossierBranch === 'function') {
    window.switchDossierBranch(tabId);
  } else if (tabId === 'interview' && typeof window.switchExamBranch === 'function') {
    window.switchExamBranch('interview');
  }
};

// Stage activation listener for on-demand lazy hydration
window.onStageActivated = (stageKey) => {
  if (stageKey === 'routine') {
    initDailyRoutine();
  } else if (stageKey === 'study') {
    loadStudyStatus();
  } else if (stageKey === 'bunki') {
    loadBunkiProfile();
    syncSlot1UI();
  } else if (stageKey === 'exams') {
    loadExamAnalytics();
    loadExam('all');
  } else if (stageKey === 'dossier') {
    loadCareer();
    loadDossierStatus();
    if (typeof window.loadGoalposts === 'function') window.loadGoalposts();
  }
};

// Expose action handlers for HTML onclick attributes
window.switchStudyBranch = switchStudyBranch;
window.switchDossierBranch = switchDossierBranch;
window.switchExamBranch = switchExamBranch;
window.toggleDrawer = toggleDrawer;
window.syncBatchGroup = syncBatchGroup;
window.searchManualVocab = searchManualVocab;
window.updateDocStatus = updateDocStatus;
window.reviewLeechAction = reviewLeechAction;
window.verifySlot1WithAnkiWeb = verifySlot1WithAnkiWeb;
window.syncSlot1UI = syncSlot1UI;
window.loadExam = loadExam;
window.submitExam = submitExam;
window.loadExamAnalytics = loadExamAnalytics;
window.speakJapanese = speakJapanese;
window.toggleInlineModel = toggleInlineModel;
window.previewDossier = previewDossier;
window.launchRoutineSlot = launchRoutineSlot;
window.markRoutineSlotDone = markRoutineSlotDone;
window.unmarkRoutineSlot = unmarkRoutineSlot;
window.toggleRoutineSlot = toggleRoutineSlot;
window.updateRoutineProgress = updateRoutineProgress;

document.addEventListener('DOMContentLoaded', () => {
  initCountdown();
  initDock();
  initViewport();
  initDragScroll();

  // Initial stage hydration (Routine & Study baseline)
  initDailyRoutine();
  loadStudyStatus();
  syncSlot1UI();
});

