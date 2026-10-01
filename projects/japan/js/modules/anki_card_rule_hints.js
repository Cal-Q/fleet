// static/js/modules/anki_card_rule_hints.js — Grammar Rule Hint Manager on Collision / Alt Rule
// Persists and renders target rule hints on front until card reaches >= 10 days cooldown.
// Strictly <= 200 lines invariant.

const STORAGE_KEY = 'anki_rule_hint_cards';

let _cachedMap = null;

export function getRuleHintMap() {
  if (_cachedMap !== null) return _cachedMap;
  try {
    if (typeof localStorage === 'undefined') {
      _cachedMap = {};
      return _cachedMap;
    }
    const raw = localStorage.getItem(STORAGE_KEY);
    _cachedMap = raw ? JSON.parse(raw) : {};
  } catch {
    _cachedMap = {};
  }
  return _cachedMap;
}

export function saveRuleHintMap(map) {
  _cachedMap = map;
  try {
    if (typeof localStorage === 'undefined') return;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  } catch {}
}

export function extractTargetRuleName(card) {
  if (!card) return '';
  if (card.rule_name) return card.rule_name;
  if (card.details?.title) return card.details.title;

  // Attempt extraction from card.meaning HTML (Bunpro title header)
  if (card.meaning && typeof card.meaning === 'string') {
    const m = card.meaning.match(/<div class="[^"]*jp-font[^"]*">([^<]+)<\/div>/);
    if (m && m[1]) return m[1].trim();
  }

  // Attempt extraction from notes or front
  if (card.notes && typeof card.notes === 'string') {
    const m = card.notes.match(/\[([^\]]+)\]/);
    if (m && m[1]) return m[1].trim();
  }

  return '';
}

export function flagCardForAltRule(card) {
  if (!card || !card.id) return '';
  const ruleName = extractTargetRuleName(card);
  const map = getRuleHintMap();
  map[String(card.id)] = {
    ruleName: ruleName || 'Regola Specifica',
    flaggedAt: Date.now(),
    initialIvl: card.ivl || 0
  };
  saveRuleHintMap(map);
  return ruleName || 'Regola Specifica';
}

export function getCardRuleHintHtml(card) {
  if (!card || !card.id) return '';
  const map = getRuleHintMap();
  const entry = map[String(card.id)];
  if (!entry) return '';

  // Rule removal condition: card interval reaches 10 days cooldown or more
  const currentIvl = card.ivl !== undefined ? card.ivl : 0;
  if (currentIvl >= 10) {
    delete map[String(card.id)];
    saveRuleHintMap(map);
    return '';
  }

  const name = entry.ruleName || 'Regola Specifica';
  return (
    `<div class="mt-2 text-center animate-info-fade select-none">` +
    `<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full ` +
    `bg-[#D97706]/20 border border-[#F59E0B]/50 text-[#FDE68A] text-xs font-semibold shadow-sm">` +
    `🎯 <b>Regola:</b> ${name}` +
    `</span></div>`
  );
}

export function checkRuleHintOnAnswer(card, newIvl) {
  if (!card || !card.id) return;
  if (newIvl >= 10) {
    const map = getRuleHintMap();
    if (map[String(card.id)]) {
      delete map[String(card.id)];
      saveRuleHintMap(map);
    }
  }
}
