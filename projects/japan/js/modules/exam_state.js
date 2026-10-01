// static/js/modules/exam_state.js — Exam State, Confidence & Unknown Characters Store
// Strictly <= 200 lines invariant.

const KEY_ANSWERS = "mext_exam_answers";
const KEY_CONFIDENCE = "mext_exam_confidence";
const KEY_UNKNOWN_CHARS = "mext_exam_unknown_chars";

let answers = {};
let confidence = {};
let unknownChars = {};
let missingPartsMode = false;

export function loadExamStateFromStorage() {
  try {
    answers = JSON.parse(localStorage.getItem(KEY_ANSWERS) || "{}");
  } catch (e) {
    answers = {};
  }
  try {
    confidence = JSON.parse(localStorage.getItem(KEY_CONFIDENCE) || "{}");
  } catch (e) {
    confidence = {};
  }
  try {
    unknownChars = JSON.parse(localStorage.getItem(KEY_UNKNOWN_CHARS) || "{}");
  } catch (e) {
    unknownChars = {};
  }
}

export function clearExamStateStorage() {
  answers = {};
  confidence = {};
  unknownChars = {};
  missingPartsMode = false;
  try {
    localStorage.removeItem(KEY_ANSWERS);
    localStorage.removeItem(KEY_CONFIDENCE);
    localStorage.removeItem(KEY_UNKNOWN_CHARS);
  } catch (e) {}
}

export function getUserAnswer(qid) {
  return answers[qid] || "";
}

export function setUserAnswer(qid, val) {
  answers[qid] = val;
  try {
    localStorage.setItem(KEY_ANSWERS, JSON.stringify(answers));
  } catch (e) {}
}

export function getAllAnswers() {
  return { ...answers };
}

export function getConfidence(qid) {
  return confidence[qid] || null;
}

export function setConfidence(qid, val) {
  confidence[qid] = val;
  try {
    localStorage.setItem(KEY_CONFIDENCE, JSON.stringify(confidence));
  } catch (e) {}
}

export function getAllConfidence() {
  return { ...confidence };
}

export function getUnknownChars(qid) {
  return unknownChars[qid] || [];
}

export function toggleUnknownChar(qid, char) {
  if (!char || !char.trim()) return;
  const list = [...(unknownChars[qid] || [])];
  const idx = list.indexOf(char);
  if (idx >= 0) {
    list.splice(idx, 1);
  } else {
    list.push(char);
  }
  unknownChars[qid] = list;
  try {
    localStorage.setItem(KEY_UNKNOWN_CHARS, JSON.stringify(unknownChars));
  } catch (e) {}
}

export function getAllUnknownChars() {
  return { ...unknownChars };
}

export function isMissingPartsActive() {
  return missingPartsMode;
}

export function setMissingPartsActive(active) {
  missingPartsMode = Boolean(active);
}
