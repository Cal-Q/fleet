// static/js/main.js — Main Application Orchestration
// Strictly <= 200 lines invariant.

import { initCountdown } from './modules/navigation.js';
import { initDock, setActiveStage, getActiveStage } from './modules/dock.js';
import { initViewport } from './modules/viewport.js';
import {
  loadStudyStatus,
  searchManualVocab,
  switchStudyBranch,
  syncBatchGroup,
  toggleDrawer,
} from './modules/study.js';
import {
  loadCareer,
  loadDossierStatus,
  updateDocStatus,
  switchDossierBranch,
} from './modules/dossier.js';
import {
  loadExam,
  loadNextBatch,
  resetExam,
  loadExamAnalytics,
  submitExam,
  switchExamBranch,
  selectExamOption,
  saveQuestionNote,
  getUserAnswer,
  goToQuestion,
  nextQuestion,
  prevQuestion,
  toggleCurrentNote,
  confirmResetExamTimer,
  toggleMissingPartsMode,
  setConfidenceLevel,
  onCharClick,
} from './modules/exams.js';
import {
  loadInterview,
  speakJapanese,
  toggleInlineModel,
} from './modules/interview.js';
import { loadResearchDossiers, previewDossier } from './modules/research.js';
import {
  initDailyRoutine,
  launchRoutineSlot,
  markRoutineSlotDone,
  unmarkRoutineSlot,
  toggleRoutineSlot,
  updateRoutineProgress,
} from './modules/routine.js';
import { syncCurriculumPlan } from './modules/routine_curriculum.js';
import { initDragScroll } from './modules/drag_scroll.js';
import {
  toggleAmbientExamAudio,
  stopAmbientExamAudio,
} from './modules/exam_audio.js';
import { initSrsPlayer } from './modules/srs_player.js';

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
  if (stageKey !== 'exams') {
    stopAmbientExamAudio();
  }
  if (stageKey === 'routine') {
    initDailyRoutine();
  } else if (stageKey === 'study') {
    loadStudyStatus();
  } else if (stageKey === 'exams') {
    loadExamAnalytics();
    loadExam('A');
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
window.loadExam = loadExam;
window.loadNextBatch = loadNextBatch;
window.resetExam = resetExam;
window.confirmResetExamTimer = confirmResetExamTimer;
window.toggleMissingPartsMode = toggleMissingPartsMode;
window.setConfidenceLevel = setConfidenceLevel;
window.onCharClick = onCharClick;
window.submitExam = submitExam;
window.selectExamOption = selectExamOption;
window.goToQuestion = goToQuestion;
window.nextQuestion = nextQuestion;
window.prevQuestion = prevQuestion;
window.toggleCurrentNote = toggleCurrentNote;
window.saveQuestionNote = saveQuestionNote;
window.getUserAnswer = getUserAnswer;
window.loadExamAnalytics = loadExamAnalytics;
window.loadInterview = loadInterview;
window.speakJapanese = speakJapanese;
window.toggleInlineModel = toggleInlineModel;
window.loadResearchDossiers = loadResearchDossiers;
window.previewDossier = previewDossier;
window.launchRoutineSlot = launchRoutineSlot;
window.markRoutineSlotDone = markRoutineSlotDone;
window.unmarkRoutineSlot = unmarkRoutineSlot;
window.toggleRoutineSlot = toggleRoutineSlot;
window.updateRoutineProgress = updateRoutineProgress;
window.toggleAmbientExamAudio = toggleAmbientExamAudio;
window.stopAmbientExamAudio = stopAmbientExamAudio;

document.addEventListener('DOMContentLoaded', () => {
  initCountdown();
  initDock();
  initViewport();
  initDragScroll();

  // Initial stage hydration (Routine & Study baseline)
  initDailyRoutine();
  syncCurriculumPlan();
  loadStudyStatus();
  initSrsPlayer();
});

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') {
    loadStudyStatus();
  }
});

