// static/js/main.js — Single-Bundle Application Orchestrator
// Strictly <= 200 lines invariant.

import { initCountdown } from './modules/dock.js';
import { initDock } from './modules/dock.js';
import { initViewport } from './modules/viewport.js';
import {
  loadStudyStatus,
  switchStudyBranch,
  toggleDrawer,
  syncBatchGroup,
  searchManualVocab,
} from './modules/study.js';
import { initSrsPlayer } from './modules/srs_player.js';
import {
  switchDossierBranch,
  loadDossierStatus,
  updateDocStatus,
} from './modules/dossier.js';
import {
  loadExam,
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

// Cache Buster Version
export const APP_BUILD_VERSION = '20260927_v300';
console.log(`[RoadToMEXT] Bootstrapping Engine Build: ${APP_BUILD_VERSION}`);

// Global Tab Switch Dispatcher
window.switchTab = (tabName) => {
  document.querySelectorAll('section[id^="section-"]').forEach((sec) => {
    sec.classList.add('hidden');
  });
  const target = document.getElementById(`section-${tabName}`);
  if (target) {
    target.classList.remove('hidden');
  }

  // Update active state on bottom dock pills
  document.querySelectorAll('#bottom-dock button').forEach((btn) => {
    btn.classList.remove('border-b-2', 'border-[#181A1B]', 'text-[#181A1B]');
    btn.classList.add('text-neutral-500');
  });
  const activeBtn = document.getElementById(`dock-${tabName}`);
  if (activeBtn) {
    activeBtn.classList.add(
      'border-b-2',
      'border-[#181A1B]',
      'text-[#181A1B]'
    );
    activeBtn.classList.remove('text-neutral-500');
  }

  // Life-cycle triggers per stage
  if (tabName !== 'exams') {
    stopAmbientExamAudio();
  }
  if (tabName === 'routine') {
    initDailyRoutine();
    syncCurriculumPlan();
  } else if (tabName === 'study') {
    loadStudyStatus();
  } else if (tabName === 'bunki') {
    if (typeof window.loadBunkiStatus === 'function') window.loadBunkiStatus();
  } else if (tabName === 'exams') {
    loadExam('A');
  } else if (tabName === 'dossier') {
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
