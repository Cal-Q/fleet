// static/js/modules/anki_web_reviewer.js
// SRS Card Grading, Leech Detection & Review Persistence (<= 200 lines, <= 100 cols)

import { queueReview, updateCachedCardReview } from './anki_web_db.js';
import { enqueueFailedCard } from './anki_web_queue.js';
import { checkRuleHintOnAnswer } from './anki_card_rule_hints.js';
import { ankiLog } from './anki_logger.js';

export function handleCardGrading(card, grade) {
  const isReviewCard = (card.queue === 2 || card.type === 2);
  const isReviewLapse = (grade === 1 && isReviewCard);
  const isLeech = isReviewLapse && ((card.lapses || 0) >= 7);

  if (grade === 1) {
    card.ivl = 0;
    if (isLeech) {
      ankiLog('WARN', 'SRS', 'LEECH_QUARANTINED', {
        cid: card.id,
        lapses: (card.lapses || 0) + 1
      });
    } else {
      enqueueFailedCard(card);
    }
  }
}

export function syncCardReview(card, grade, timeMs, currentDeckId) {
  const payload = {
    card_id: card.id,
    grade,
    time_ms: timeMs,
    timestamp: Date.now()
  };
  const targetDeckId = card.did || currentDeckId || 0;
  const deferWrite = (fn) => {
    if (typeof window !== 'undefined' && 'requestIdleCallback' in window) {
      window.requestIdleCallback(fn, { timeout: 1500 });
    } else {
      setTimeout(fn, 600);
    }
  };
  deferWrite(() => updateCachedCardReview(targetDeckId, card.id, grade));

  if (!navigator.onLine) {
    queueReview(payload);
    checkRuleHintOnAnswer(card, card.ivl || 0);
    return;
  }

  fetch('/api/anki/review', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
    .then((r) => (r.ok ? r.json() : null))
    .then((d) => {
      checkRuleHintOnAnswer(card, d?.new_ivl ?? (card.ivl || 0));
    })
    .catch(() => {
      queueReview(payload);
    });
}
