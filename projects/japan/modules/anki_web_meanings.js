// static/js/modules/anki_web_meanings.js — Structured Multi-Reading & Meanings Parser
// Strictly <= 200 lines invariant.

export function parseMeaningBlocks(meaningHtml, primaryReadingHtml = '') {
  if (!meaningHtml) return [];
  const cleanPrimary = (primaryReadingHtml || '')
    .replace(/\[sound:[^\]]+\]/g, '')
    .replace(/<[^>]+>/g, '')
    .trim();
  const raw = (meaningHtml || '')
    .replace(/\[sound:[^\]]+\]/g, '')
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n');
  const rawBlocks = raw.split(/<br\s*\/?>\s*<br\s*\/?>|\n\n/);

  const parsedReadings = [];

  for (let b of rawBlocks) {
    b = b.trim();
    if (!b) continue;
    const parts = b.split(/<br\s*\/?>|\n/).map(p => p.trim()).filter(Boolean);
    if (!parts.length) continue;

    let kana = '', senseLines = [];
    if (!parts[0].startsWith('-') && !parts[0].startsWith('•')) {
      kana = parts[0].replace(/<[^>]+>/g, '').trim();
      senseLines = parts.slice(1);
    } else {
      kana = cleanPrimary || '標準';
      senseLines = parts;
    }

    const scoredSenses = [];
    let nameCount = 0;
    for (const s of senseLines) {
      const cleanSense = s.replace(/^[-•\s]+/, '').trim();
      if (!cleanSense) continue;
      const lower = cleanSense.toLowerCase();
      const isName = lower.includes('family or surname') || lower.includes('given name') || lower.includes('place name') || lower.includes('unclassified name');
      const isCommon = !isName && !lower.includes('archaic') && !lower.includes('obsolete') && !lower.includes('rare');
      const score = isCommon ? 100 : (!isName ? 10 : 1);
      if (isName) nameCount++;
      scoredSenses.push({ score, text: cleanSense });
    }

    scoredSenses.sort((a, b) => b.score - a.score);
    const senses = scoredSenses.map(x => x.text);

    const isPrimary = cleanPrimary && (kana === cleanPrimary || cleanPrimary.includes(kana) || kana.includes(cleanPrimary));
    const hasRealWords = scoredSenses.some(x => x.score >= 10);

    let rScore = 0;
    if (isPrimary) rScore += 1000;
    if (hasRealWords) rScore += 500;
    rScore += senses.length * 5 - nameCount * 30;

    parsedReadings.push({
      kana,
      senses,
      score: rScore,
      isPrimary,
      topSnippet: senses[0] ? (senses[0].length > 28 ? senses[0].slice(0, 28) + '…' : senses[0]) : ''
    });
  }

  parsedReadings.sort((a, b) => b.score - a.score);
  return parsedReadings;
}

export function renderReadingsAndMeanings(card, onReadingChange) {
  const readingContainer = document.getElementById('ankiCardReading');
  const meaningContainer = document.getElementById('ankiCardMeaning');
  if (!readingContainer || !meaningContainer) return;

  if (card.meaning && card.meaning.includes('bunpro-card-details')) {
    readingContainer.innerHTML = card.reading || '';
    meaningContainer.innerHTML = card.meaning;
    return;
  }

  const parsed = (Array.isArray(card.readings) && card.readings.length > 0)
    ? card.readings
    : parseMeaningBlocks(card.meaning, card.reading);

  if (!parsed.length) {
    readingContainer.innerHTML = card.reading || '';
    meaningContainer.innerHTML = card.meaning || '';
    return;
  }

  const renderSelectedReading = (idx) => {
    const active = parsed[idx] || parsed[0];
    const senses = Array.isArray(active.senses) ? active.senses : [];
    if (!senses.length) {
      meaningContainer.innerHTML = '<span class="text-neutral-400 italic">Nessun significato disponibile</span>';
      return;
    }
    meaningContainer.innerHTML = senses.map(s => `
      <div class="flex items-start gap-2 py-0.5 leading-relaxed">
        <span class="text-[#42A5F5] font-bold text-xs flex-shrink-0 mt-0.5">•</span>
        <span class="text-white font-medium text-xs sm:text-sm">${s}</span>
      </div>
    `).join('');
  };

  if (parsed.length <= 1) {
    readingContainer.innerHTML = `<span class="text-white font-bold text-lg sm:text-xl jp-font tracking-wide">${parsed[0].kana}</span>`;
    renderSelectedReading(0);
  } else {
    readingContainer.innerHTML = `
      <div class="flex items-center justify-center gap-2 w-full max-w-xs px-2 animate-info-fade">
        <span class="text-[10px] font-mono text-neutral-400 uppercase tracking-wider flex-shrink-0">Lettura:</span>
        <select id="ankiReadingSelect" class="bg-[#1A1A1A] hover:bg-[#252525] text-white font-bold text-sm sm:text-base border border-[#3C3C3C] hover:border-[#42A5F5] rounded-lg px-3 py-1 jp-font cursor-pointer focus:outline-none focus:border-[#42A5F5] transition shadow-sm text-center min-w-[140px]">
          ${parsed.map((r, i) => `<option value="${i}">${r.kana}</option>`).join('')}
        </select>
      </div>
    `;

    const selectEl = document.getElementById('ankiReadingSelect');
    if (selectEl) {
      selectEl.addEventListener('change', (e) => {
        const idx = parseInt(e.target.value, 10) || 0;
        renderSelectedReading(idx);
        if (typeof onReadingChange === 'function') onReadingChange(parsed[idx]);
      });
    }

    renderSelectedReading(0);
  }
}
