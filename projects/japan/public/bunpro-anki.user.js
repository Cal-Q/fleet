// ==UserScript==
// @name         Bunpro: Copy for Anki (Native UI Integration)
// @namespace    http://tampermonkey.net/
// @version      42.0
// @description  Flawlessly integrates Anki extraction tools into Bunpro's native UI design. Synced with VPS database.
// @author       You
// @match        https://bunpro.jp/*
// @grant        GM_setClipboard
// @grant        GM.setClipboard
// @grant        GM_download
// @grant        GM.xmlHttpRequest
// @connect      82.165.61.120
// @connect      japan.calq.it
// @connect      127.0.0.1
// ==/UserScript==

(function() {
    'use strict';
    console.log("🚀 BUNPRO ANKI SCRIPT EXECUTING! 🚀");

    // --- Configuration ---
    const VPS_BASE_URL = "https://japan.calq.it";
    const ANKI_DECK_NAME = "[JAP]::[TRAVEL]::[1] Jap Sentences";
    const ANKI_REVIEW_DECK_NAME = "[JAP]::[TRAVEL]::[2] Jap Review Sentences";
    const ANKI_MODEL_NAME = "Jap Sentences";
    // Vocab (sendVocabToAnki) goes through the server's relay instead of local AnkiConnect, so it
    // works without Anki open on this machine — see server.js's /api/vocab-relay.
    const VOCAB_RELAY_URL = VPS_BASE_URL + "/api/vocab-relay";

    // --- 1. Global State & Native CSS ---
    const audioMap = {};
    let parsedNextData = false;
    let vpsCopiedItems = []; // Stored as array of URLs

    function normalizeUrl(u) {
        if (!u) return u;
        try { return decodeURI(u); } catch(e) { return u; }
    }
    
    function isItemCopied(url) {
        if (!url) return false;
        const norm = normalizeUrl(url);
        return vpsCopiedItems.some(u => normalizeUrl(u) === norm);
    }

    const style = document.createElement('style');
    style.textContent = `
        /* General Page Tools */
        .tm-anki-btn-container {
            display: flex !important; justify-content: center !important; align-items: center !important; gap: 8px !important; margin: 12px 0 !important;
            opacity: 0.85; transition: opacity 0.2s ease-in-out; width: 100% !important; z-index: 9999 !important;
        }
        .tm-anki-btn-container:hover, .tm-anki-btn-container.tm-always-visible { opacity: 1 !important; }

        .tm-anki-btn {
            background: var(--c-secondary-bg, #2b2d3a) !important; 
            border: 1px solid var(--c-rim, #4a4d62) !important; 
            color: var(--c-primary-fg, #ffffff) !important;
            border-radius: 9999px !important; padding: 6px 14px !important; font-size: 13px !important; font-family: inherit !important;
            font-weight: 600 !important; cursor: pointer !important; display: inline-flex !important; align-items: center !important; gap: 6px !important;
            transition: all 0.2s ease !important; box-shadow: 0 2px 4px rgba(0,0,0,0.15) !important;
        }
        .tm-anki-btn:hover {
            background: rgb(var(--c-primary-accent, 59, 130, 246)) !important; 
            color: var(--c-primary-contrast, #ffffff) !important; 
            border-color: rgb(var(--c-primary-accent, 59, 130, 246)) !important;
            transform: translateY(-1px);
        }
        .tm-anki-btn:disabled { opacity: 0.5 !important; cursor: not-allowed !important; }
        .tm-anki-btn svg { width: 14px !important; height: 14px !important; flex-shrink: 0 !important; }

        .tm-anki-btn.success { background: rgba(34, 197, 94, 0.2) !important; color: #22c55e !important; border-color: #22c55e !important; }
        .tm-anki-btn.error { background: rgba(239, 68, 68, 0.2) !important; color: #ef4444 !important; border-color: #ef4444 !important; }

        /* Floating Panels (Multi-Select & Library Output) */
        .tm-floating-panel {
            position: fixed; bottom: 24px; right: 24px; z-index: 999999;
            background: var(--c-primary-bg, #1e1f29); color: var(--c-primary-fg, #ffffff);
            padding: 16px; border-radius: 12px; border: 1px solid var(--c-rim, #3f4152);
            box-shadow: 0 10px 25px -5px rgba(0,0,0,0.2), 0 8px 10px -6px rgba(0,0,0,0.1);
            display: flex; flex-direction: column; gap: 12px; font-family: inherit;
            min-width: 250px;
        }
        .tm-floating-btn {
            background: rgb(var(--c-primary-accent, 59, 130, 246)); color: var(--c-primary-contrast, #ffffff);
            border: none; padding: 10px 16px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 13px;
            transition: opacity 0.2s; display: flex; justify-content: center; align-items: center; gap: 6px;
        }
        .tm-floating-btn:hover { opacity: 0.85; }
        .tm-floating-btn:disabled { background: var(--c-rim, #3f4152); cursor: not-allowed; color: var(--c-secondary-fg, #888); }

        /* Vocab Toolkit UI */
        .tm-vocab-meanings-container { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin-top: 10px; }
        .tm-vocab-meaning-btn {
            background: var(--c-secondary-bg, #2b2d3a); border: 1px solid var(--c-rim, #4a4d62); color: var(--c-primary-fg, #ffffff);
            border-radius: 8px; padding: 6px 12px; font-size: 14px; cursor: pointer; transition: all 0.2s ease; box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            display: inline-flex; align-items: center; justify-content: center; gap: 6px;
        }
        .tm-vocab-meaning-btn:hover { background: rgb(var(--c-primary-accent, 59, 130, 246)); color: var(--c-primary-contrast, #ffffff); border-color: rgb(var(--c-primary-accent, 59, 130, 246)); }
        .tm-vocab-meaning-btn svg { width: 14px; height: 14px; flex-shrink: 0; }
        .tm-vocab-meaning-btn.success { background: rgba(34, 197, 94, 0.2) !important; color: #22c55e !important; border-color: #22c55e !important; }
        .tm-vocab-meaning-btn.error { background: rgba(239, 68, 68, 0.2) !important; color: #ef4444 !important; border-color: #ef4444 !important; }

        /* Grammar Library Native UI Integration */
        .tm-copied-btn-state {
            background: rgba(34, 197, 94, 0.15) !important; color: #16a34a !important; border: 1px solid #22c55e !important;
        }
        .tm-copied-tile a.group {
            outline: 2px solid #22c55e !important; outline-offset: -2px !important; background: rgba(34, 197, 94, 0.05) !important;
        }
        .tm-bulk-btn-wrapper { margin-bottom: 16px; display: flex; justify-content: flex-end; width: 100%; }
        .tm-bulk-btn { padding: 8px 16px; border-radius: 8px; font-size: 13px; }
    `;
    document.head.appendChild(style);

    const copyIcon = `<svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`;
    const ankiIcon = `<svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 17 22 12"></polyline></svg>`;

    // --- VPS DB SYNC ---
    async function loadCopiedItems() {
        return new Promise((resolve) => {
            GM.xmlHttpRequest({
                method: "GET",
                url: `${VPS_BASE_URL}/api/copied-items`,
                onload: function(response) {
                    try {
                        if (response.status === 200) vpsCopiedItems = JSON.parse(response.responseText);
                        resolve();
                    } catch (e) { resolve(); }
                },
                onerror: () => resolve()
            });
        });
    }

    async function toggleCopiedItem(url, isCopied) {
        return new Promise((resolve) => {
            const method = isCopied ? 'DELETE' : 'POST';
            GM.xmlHttpRequest({
                method: method,
                url: `${VPS_BASE_URL}/api/copied-items`,
                headers: { 'Content-Type': 'application/json' },
                data: JSON.stringify({ url }),
                onload: function() {
                    if (isCopied) {
                        const norm = normalizeUrl(url);
                        vpsCopiedItems = vpsCopiedItems.filter(u => normalizeUrl(u) !== norm);
                    } else {
                        if (!isItemCopied(url)) {
                            vpsCopiedItems.push(url);
                        }
                    }
                    resolve();
                },
                onerror: () => resolve()
            });
        });
    }

    // --- ANKI CONNECT INTEGRATION (Sentences) ---
    async function sendToAnki(items) {
        let notes = items.map(item => {
            let audioData = undefined;
            if (item.audioUrl) {
                audioData = [{
                    url: item.audioUrl,
                    filename: item.fileName,
                    fields: ["Audio"]
                }];
            }

            return {
                deckName: item.deckName || ANKI_DECK_NAME,
                modelName: item.modelName || ANKI_MODEL_NAME,
                mainField: item.mainField || "Japanese",
                fields: {
                    "Japanese": item.cleanJP,
                    "English": item.cleanEN
                },
                options: { allowDuplicate: false },
                tags: ["bunpro"],
                audio: audioData
            };
        });

        return new Promise((resolve) => {
            const data = { action: "addNotes", version: 6, params: { notes: notes } };
            GM.xmlHttpRequest({
                method: "POST",
                url: `${VPS_BASE_URL}/api/sentence-relay`,
                headers: { 'Content-Type': 'application/json' },
                data: JSON.stringify(data),
                onload: function(response) {
                    try {
                        const result = JSON.parse(response.responseText);
                        if (result.error) {
                            console.error("AnkiConnect error:", result.error);
                            resolve(false);
                        } else {
                            resolve(true);
                        }
                    } catch (e) { resolve(false); }
                },
                onerror: function(e) { resolve(false); }
            });
        });
    }

    // --- ANKI CONNECT INTEGRATION (Vocab) ---
    async function sendVocabToAnki(meaning, fullKana, button) {
        const originalHTML = button.innerHTML;
        button.innerHTML = "...";
        button.disabled = true;

        const TARGET_DECK = "[SOURCE] English -> Kana";
        const TARGET_MODEL = "[SOURCE] English To Kana";
        
        const safeMeaning = meaning.replace(/"/g, '\\"');
        const query = `deck:"${TARGET_DECK}" "Front:${safeMeaning}"`;

        function resetBtn() {
            setTimeout(() => { button.classList.remove('success', 'error'); button.innerHTML = originalHTML; button.disabled = false; }, 2500);
        }

        function showError(msg) {
            button.classList.add('error');
            button.innerHTML = msg;
            resetBtn();
        }

        function addNewNote() {
            let notes = [{
                deckName: TARGET_DECK,
                modelName: TARGET_MODEL,
                fields: { "Front": meaning, "Back": fullKana },
                options: { allowDuplicate: false },
                tags: ["bunpro", "vocab"]
            }];
            
            GM.xmlHttpRequest({
                method: "POST",
                url: VOCAB_RELAY_URL,
                data: JSON.stringify({ action: "addNotes", version: 6, params: { notes: notes } }),
                onload: function(response) {
                    try {
                        const result = JSON.parse(response.responseText);
                        const errorStr = result.error ? String(result.error).toLowerCase() : "";
                        if (errorStr.includes('duplicate') || (result.result && result.result[0] === null)) {
                            button.classList.add('error');
                            button.innerHTML = `Duplicate`;
                        } else if (result.error) {
                            showError("Error");
                            return;
                        } else {
                            button.classList.add('success');
                            button.innerHTML = `Sent!`;
                        }
                    } catch (e) { showError("Error"); return; }
                    resetBtn();
                },
                onerror: () => showError("Error")
            });
        }

        GM.xmlHttpRequest({
            method: "POST",
            url: VOCAB_RELAY_URL,
            data: JSON.stringify({ action: "findNotes", version: 6, params: { query: query } }),
            onload: function(res1) {
                try {
                    let noteIds = JSON.parse(res1.responseText).result || [];
                    if (noteIds.length > 0) {
                        GM.xmlHttpRequest({
                            method: "POST",
                            url: VOCAB_RELAY_URL,
                            data: JSON.stringify({ action: "notesInfo", version: 6, params: { notes: noteIds } }),
                            onload: function(res2) {
                                try {
                                    let notesInfo = JSON.parse(res2.responseText).result || [];
                                    let exactMatchNote = notesInfo.find(n => n.fields && n.fields.Front && n.fields.Front.value === meaning);
                                    
                                    if (exactMatchNote) {
                                        let currentBack = exactMatchNote.fields.Back.value;
                                        let cleanBack = currentBack.replace(/<[^>]*>?/gm, '');
                                        
                                        if (cleanBack.includes(fullKana)) {
                                            button.classList.add('error');
                                            button.innerHTML = `Duplicate`;
                                            resetBtn();
                                        } else {
                                            let newBack = currentBack;
                                            if (newBack.length > 0) {
                                                newBack += `<br>${fullKana}`;
                                            } else {
                                                newBack = fullKana;
                                            }
                                            
                                            GM.xmlHttpRequest({
                                                method: "POST",
                                                url: VOCAB_RELAY_URL,
                                                data: JSON.stringify({
                                                    action: "updateNoteFields",
                                                    version: 6, 
                                                    params: { 
                                                        note: {
                                                            id: exactMatchNote.noteId,
                                                            fields: { "Back": newBack }
                                                        }
                                                    } 
                                                }),
                                                onload: function(res3) {
                                                    try {
                                                        let uRes = JSON.parse(res3.responseText);
                                                        if (uRes.error) {
                                                            showError("Error");
                                                        } else {
                                                            button.classList.add('success');
                                                            button.innerHTML = `Appended!`;
                                                            resetBtn();
                                                        }
                                                    } catch(e) { showError("Error"); }
                                                }
                                            });
                                        }
                                    } else {
                                        addNewNote();
                                    }
                                } catch(e) { showError("Error"); }
                            }
                        });
                    } else {
                        addNewNote();
                    }
                } catch(e) { showError("Error"); }
            },
            onerror: () => showError("Error")
        });
    }

    let libFloatingPanel = null;
    let floatingPanel = null;
    let countSpan = null;
    let exportBtn = null;

    function manageFloatingPanelsVisibility() {
        const isQuiz = window.location.pathname.startsWith('/learn') || 
                       window.location.pathname.startsWith('/reviews') || 
                       window.location.pathname.startsWith('/cram') ||
                       window.location.pathname.startsWith('/deck');
        if (libFloatingPanel) {
            libFloatingPanel.style.display = isQuiz ? 'none' : 'flex';
        }
        if (floatingPanel) {
            const count = document.querySelectorAll('.tm-select-cb:checked').length;
            floatingPanel.style.display = (count > 0 && !isQuiz) ? 'flex' : 'none';
        }
    }

    function initLibraryFloatingPanel() {
        if (libFloatingPanel) return;

        libFloatingPanel = document.createElement('div');
        libFloatingPanel.className = 'tm-floating-panel';
        libFloatingPanel.style.width = '250px';

        const title = document.createElement('div');
        title.innerHTML = `<b>Anki Library Exporter</b>`;
        title.style.textAlign = 'center';
        title.style.fontSize = '13px';

        const sendAnkiBtn = document.createElement('button');
        sendAnkiBtn.className = 'tm-floating-btn';
        sendAnkiBtn.innerHTML = `${ankiIcon} Send Selected to Anki (0)`;
        sendAnkiBtn.id = 'tm-send-selected-btn';
        sendAnkiBtn.style.width = '100%';
        
        sendAnkiBtn.onclick = async () => {
            const checkboxes = Array.from(document.querySelectorAll('.tm-library-cb:checked'));
            if (checkboxes.length === 0) return;

            sendAnkiBtn.disabled = true;
            sendAnkiBtn.innerText = `Fetching ${checkboxes.length} points...`;

            try {
                const results = await Promise.all(
                    checkboxes.map(async (cb, i) => {
                        const url = cb.dataset.url;
                        const item = cb.closest('li');
                        const markBtn = item ? item.querySelector('.tm-mark-copied-btn') : null;

                        const res = await extractGrammarPage(url);
                        if (markBtn && !markBtn.classList.contains('tm-copied-btn-state')) {
                            toggleCopiedItem(url, false).then(() => {
                                markBtn.innerHTML = 'Copied ✓';
                                markBtn.className = 'tm-mark-copied-btn inline-flex items-center justify-center gap-4 rounded-half px-6 py-2 font-bold transition-colors text-detail tm-copied-btn-state';
                                if (item) item.classList.add('tm-copied-tile');
                            });
                        }
                        cb.checked = false;

                        return res.map((grammarItem, gIdx) => ({
                            cleanJP: grammarItem.cleanJP,
                            cleanEN: grammarItem.cleanEN,
                            audioUrl: grammarItem.audioUrl,
                            fileName: `bunpro_lib_${getSafeId()}_${i}_${gIdx}.mp3`
                        }));
                    })
                );

                const items = results.flat();
                if (items.length > 0) {
                    sendAnkiBtn.innerText = `Sending ${items.length} cards...`;
                    const success = await sendToAnki(items);
                    if (success) {
                        sendAnkiBtn.innerHTML = `Sent ${items.length} cards!`;
                    } else {
                        sendAnkiBtn.innerHTML = `Error sending to Anki`;
                    }
                } else {
                    sendAnkiBtn.innerHTML = `No cards found`;
                }
            } catch (err) {
                console.error("[Bunpro Anki] Library export error:", err);
                sendAnkiBtn.innerHTML = `Error: ${err.message || 'Check Console'}`;
            }

            updateLibraryFloatingPanel();
            setTimeout(() => {
                sendAnkiBtn.innerHTML = `${ankiIcon} Send Selected to Anki (0)`;
                sendAnkiBtn.disabled = false;
            }, 3000);
        };

        libFloatingPanel.appendChild(title);
        libFloatingPanel.appendChild(sendAnkiBtn);
        document.body.appendChild(libFloatingPanel);
        manageFloatingPanelsVisibility();
    }

    function updateLibraryFloatingPanel() {
        manageFloatingPanelsVisibility();
        const selected = document.querySelectorAll('.tm-library-cb:checked');
        const btn = document.getElementById('tm-send-selected-btn');
        if (btn) btn.innerHTML = `${ankiIcon} Send Selected to Anki (${selected.length})`;
    }

    // --- 2. Dynamic Audio Finder ---
    function makeAbsoluteUrl(url) {
        if (!url) return null;
        if (url.startsWith('//')) return 'https:' + url;
        if (!url.startsWith('http')) return new URL(url, 'https://bunpro.jp').href;
        return url;
    }

    function searchForAudio(obj) {
        if (!obj || typeof obj !== 'object') return;
        let foundAudio = obj.audio_url || obj.male_audio_url || obj.female_audio_url || obj.audio_link || obj.male_audio || obj.female_audio || obj.audio;
        let foundJp = obj.japanese || obj.sentence || obj.text;
        let foundId = obj.id || obj.sentence_id || obj.study_question_id || obj.example_id;

        if (foundAudio && typeof foundAudio === 'string' && foundAudio.match(/\.(mp3|m4a|wav|ogg)/i)) {
            let absUrl = makeAbsoluteUrl(foundAudio);
            if (foundId) audioMap[foundId.toString()] = absUrl;
            if (foundJp && typeof foundJp === 'string') {
                let cleanJp = foundJp.replace(/<[^>]*>?/gm, '').replace(/[^\p{L}\p{N}]/gu, '');
                audioMap[cleanJp] = absUrl;
            }
        }
        for (let key in obj) {
            if (obj.hasOwnProperty(key) && typeof obj[key] === 'object' && obj[key] !== null) searchForAudio(obj[key]);
        }
    }

    function extractAudioData() {
        if (parsedNextData) return;
        try {
            const nextDataScript = document.getElementById('__NEXT_DATA__');
            if (nextDataScript) {
                const data = JSON.parse(nextDataScript.textContent);
                searchForAudio(data);
                parsedNextData = true;
            }
        } catch (e) {}
    }

    if (!window.tmFetchIntercepted) {
        window.tmFetchIntercepted = true;
        const originalFetch = window.fetch;
        window.fetch = async function() {
            const response = await originalFetch.apply(this, arguments);
            try {
                const clone = response.clone();
                clone.json().then(data => searchForAudio(data)).catch(e => {});
            } catch (e) {}
            return response;
        };
    }

    function getAudioUrlForBlock(block) {
        extractAudioData();

        const idMatch = block.id.match(/\d+/);
        if (idMatch && audioMap[idMatch[0]]) return audioMap[idMatch[0]];

        const jpElement = block.querySelector('.bp-ddw');
        let rawJp = "";
        if (jpElement) {
            const clone = jpElement.cloneNode(true);
            clone.querySelectorAll('rp, rt').forEach(el => el.remove());
            rawJp = clone.textContent.trim();
            let cleanJp = rawJp.replace(/[^\p{L}\p{N}]/gu, '');
            if (audioMap[cleanJp]) return audioMap[cleanJp];
        }

        const source = block.querySelector('audio source');
        if (source && source.getAttribute('src')) return makeAbsoluteUrl(source.getAttribute('src'));
        const audio = block.querySelector('audio');
        if (audio && audio.getAttribute('src')) return makeAbsoluteUrl(audio.getAttribute('src'));

        if (rawJp) return `https://dk3kgylsgq3k1.cloudfront.net/audio/vocab/tts/${encodeURIComponent(rawJp)}-male.mp3`;
        return null;
    }

    function getSafeId() {
        return Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 6);
    }

    function getCleanJapanese(container) {
        if (!container) return "";
        let htmlStr = "";
        const ddwElements = container.querySelectorAll('.bp-ddw');
        if (ddwElements.length > 0) {
            ddwElements.forEach(el => {
                const clone = el.cloneNode(true);
                clone.querySelectorAll('rp').forEach(rp => rp.remove());
                const allElements = clone.getElementsByTagName("*");
                for (let i = 0; i < allElements.length; i++) {
                    while (allElements[i].attributes.length > 0) allElements[i].removeAttribute(allElements[i].attributes[0].name);
                }
                htmlStr += clone.innerHTML;
            });
        } else {
            const clone = container.cloneNode(true);
            clone.querySelectorAll('rp').forEach(rp => rp.remove());
            const allElements = clone.getElementsByTagName("*");
            for (let i = 0; i < allElements.length; i++) {
                while (allElements[i].attributes.length > 0) allElements[i].removeAttribute(allElements[i].attributes[0].name);
            }
            htmlStr = clone.innerHTML;
        }
        htmlStr = htmlStr.replace(/\s{2,}/g, ' ').trim();
        htmlStr = htmlStr.replace(/\s+([。、！？.,!?])/g, '$1');
        return htmlStr.replace(/;/g, ',').replace(/\n/g, ' ');
    }

    function getCleanEnglish(element) {
        if (!element) return "";
        let textStr = element.textContent;
        textStr = textStr.replace(/\s{2,}/g, ' ').trim();
        textStr = textStr.replace(/\s+([.,!?。、！？])/g, '$1');
        if (textStr.length > 0) textStr = textStr.charAt(0).toUpperCase() + textStr.slice(1);
        return textStr.replace(/;/g, ',').replace(/\n/g, ' ');
    }

    async function smartCopy(htmlContent, textContent, button) {
        let success = false;
        try {
            if (navigator.clipboard && navigator.clipboard.write) {
                const blobText = new Blob([textContent], { type: 'text/plain' });
                const blobHtml = new Blob([htmlContent], { type: 'text/html' });
                await navigator.clipboard.write([new ClipboardItem({ "text/plain": blobText, "text/html": blobHtml })]);
                success = true;
            }
        } catch (e) {}

        if (!success && typeof GM_setClipboard !== 'undefined') {
            try { GM_setClipboard(textContent, 'text'); success = true; } catch (e) {}
        }

        const originalHTML = button.dataset.originalHtml || button.innerHTML;
        button.dataset.originalHtml = originalHTML;

        if (success) {
            button.classList.add('success');
            button.innerHTML = `Copied!`;
        } else {
            button.classList.add('error');
            button.innerHTML = `Error`;
        }
        setTimeout(() => { button.classList.remove('success', 'error'); button.innerHTML = originalHTML; }, 1500);
    }

    async function extractGrammarPage(url) {
        try {
            const res = await fetch(url);
            const html = await res.text();
            const doc = new DOMParser().parseFromString(html, "text/html");

            const nextDataScript = doc.getElementById('__NEXT_DATA__');
            if (nextDataScript) {
                const data = JSON.parse(nextDataScript.textContent);
                searchForAudio(data);
            }

            const examplesHeader = doc.getElementById('examples');
            if (!examplesHeader) return [];
            const examplesWrapper = examplesHeader.parentElement;
            if (!examplesWrapper) return [];

            const studyBlocks = Array.from(examplesWrapper.querySelectorAll('li[id^="study-question-"]'));
            const count = Math.min(studyBlocks.length, 5);
            let results = [];

            for (let i = 0; i < count; i++) {
                const block = studyBlocks[i];
                const jpElement = block.querySelector('.bp-ddw') || block;
                const enElement = block.querySelector('.bp-sdw');

                const cleanJP = getCleanJapanese(jpElement);
                const cleanEN = getCleanEnglish(enElement);

                let audioUrl = null;
                const source = block.querySelector('audio source');
                if (source && source.getAttribute('src')) audioUrl = makeAbsoluteUrl(source.getAttribute('src'));
                if (!audioUrl) {
                    const audio = block.querySelector('audio');
                    if (audio && audio.getAttribute('src')) audioUrl = makeAbsoluteUrl(audio.getAttribute('src'));
                }
                if (!audioUrl) {
                    let rawHtml = block.outerHTML.replace(/\\\//g, '/');
                    const regexMatch = rawHtml.match(/(https?:)?\/\/[^"'\s><]+\.(?:mp3|m4a|wav|ogg)[^"'\s><]*/i);
                    if (regexMatch) audioUrl = makeAbsoluteUrl(regexMatch[0]);
                }
                if (!audioUrl) {
                    const idMatch = block.id.match(/\d+/);
                    if (idMatch && audioMap[idMatch[0]]) audioUrl = audioMap[idMatch[0]];
                }
                if (!audioUrl && jpElement) {
                    const clone = jpElement.cloneNode(true);
                    clone.querySelectorAll('rp, rt').forEach(el => el.remove());
                    let cleanJp = clone.textContent.trim().replace(/[^\p{L}\p{N}]/gu, '');
                    if (audioMap[cleanJp]) audioUrl = audioMap[cleanJp];
                }
                
                results.push({ cleanJP, cleanEN, audioUrl });
            }
            return results;
        } catch (e) {
            return [];
        }
    }

    function scanAndAddLibraryTools() {
        const grammarItems = document.querySelectorAll('li[id^="grammar_point-id-"]');
        if (grammarItems.length === 0) return;

        initLibraryFloatingPanel();

        grammarItems.forEach(item => {
            if (item.dataset.tmLibraryProcessed === "true") return;
            item.dataset.tmLibraryProcessed = "true";

            const linkEl = item.querySelector('a[href^="https://bunpro.jp/grammar_points/"], a[href^="/grammar_points/"]');
            if (!linkEl) return;

            const url = linkEl.href;
            const contentDiv = item.querySelector('.pr-44');
            if (!contentDiv) return;

            const isCopied = isItemCopied(url);
            if (isCopied) item.classList.add('tm-copied-tile');

            const toolbar = document.createElement('div');
            toolbar.className = 'flex flex-wrap gap-4 mt-6 pt-4 w-full relative z-10';
            toolbar.style.borderTop = '1px dashed var(--c-rim)';
            toolbar.onclick = (e) => { e.preventDefault(); e.stopPropagation(); };

            const selectLabel = document.createElement('label');
            selectLabel.className = 'inline-flex items-center justify-center gap-4 rounded-half px-6 py-2 font-bold text-primary-fg bg-secondary-bg border border-rim hover:bg-tertiary-bg transition-colors cursor-pointer text-detail';
            
            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.className = 'tm-library-cb';
            cb.dataset.url = url;
            cb.style.cssText = 'width:12px; height:12px; cursor:pointer; margin:0; accent-color: rgb(var(--c-primary-accent));';

            const spanText = document.createElement('span');
            spanText.innerText = 'Select';
            selectLabel.appendChild(cb);
            selectLabel.appendChild(spanText);

            selectLabel.onclick = (e) => {
                e.preventDefault(); e.stopPropagation();
                cb.checked = !cb.checked;
                updateLibraryFloatingPanel();
            };

            const fetchBtn = document.createElement('button');
            fetchBtn.className = 'tm-fetch-one-btn inline-flex items-center justify-center gap-4 rounded-half px-6 py-2 font-bold text-primary-contrast transition-colors text-detail';
            fetchBtn.style.background = 'rgb(var(--c-primary-accent))';
            fetchBtn.innerHTML = `${ankiIcon} Fetch & Send 5`;

            const markBtn = document.createElement('button');
            markBtn.className = `tm-mark-copied-btn inline-flex items-center justify-center gap-4 rounded-half px-6 py-2 font-bold transition-colors text-detail ${isCopied ? 'tm-copied-btn-state' : 'text-primary-fg bg-secondary-bg border border-rim hover:bg-tertiary-bg'}`;
            markBtn.innerHTML = isCopied ? 'Copied ✓' : 'Mark Copied';

            markBtn.onclick = async (e) => {
                e.preventDefault(); e.stopPropagation();
                const currentlyCopied = isItemCopied(url);
                await toggleCopiedItem(url, currentlyCopied);

                if (currentlyCopied) {
                    markBtn.innerHTML = 'Mark Copied';
                    markBtn.className = 'tm-mark-copied-btn inline-flex items-center justify-center gap-4 rounded-half px-6 py-2 font-bold transition-colors text-detail text-primary-fg bg-secondary-bg border border-rim hover:bg-tertiary-bg';
                    item.classList.remove('tm-copied-tile');
                } else {
                    markBtn.innerHTML = 'Copied ✓';
                    markBtn.className = 'tm-mark-copied-btn inline-flex items-center justify-center gap-4 rounded-half px-6 py-2 font-bold transition-colors text-detail tm-copied-btn-state';
                    item.classList.add('tm-copied-tile');
                }
            };

            fetchBtn.onclick = async (e) => {
                e.preventDefault(); e.stopPropagation();
                fetchBtn.innerHTML = '...';
                fetchBtn.style.opacity = '0.5';
                fetchBtn.disabled = true;

                const res = await extractGrammarPage(url);
                let items = [];
                for (const grammarItem of res) {
                    items.push({
                        cleanJP: grammarItem.cleanJP,
                        cleanEN: grammarItem.cleanEN,
                        audioUrl: grammarItem.audioUrl,
                        fileName: `bunpro_lib_${getSafeId()}_single.mp3`
                    });
                }

                if (items.length > 0) {
                    const success = await sendToAnki(items);
                    if (success && !markBtn.classList.contains('tm-copied-btn-state')) markBtn.click();
                }

                fetchBtn.innerHTML = `${ankiIcon} Fetch & Send 5`;
                fetchBtn.style.opacity = '1';
                fetchBtn.disabled = false;
            };

            toolbar.appendChild(selectLabel);
            toolbar.appendChild(fetchBtn);
            toolbar.appendChild(markBtn);
            contentDiv.appendChild(toolbar);
        });
    }

    function initFloatingPanel() {
        if (floatingPanel) return;
        floatingPanel = document.createElement('div');
        floatingPanel.className = 'tm-floating-panel';
        floatingPanel.style.display = 'none'; // Hidden by default

        const title = document.createElement('div');
        title.innerHTML = `<b>Anki Exporter</b>`;
        title.style.textAlign = 'center';
        title.style.fontSize = '12px';

        exportBtn = document.createElement('button');
        exportBtn.className = 'tm-floating-btn';
        exportBtn.innerHTML = `${ankiIcon} Send <span id="tm-bulk-count">0</span> to Anki`;
        exportBtn.onclick = handleMultiExport;

        floatingPanel.appendChild(title);
        floatingPanel.appendChild(exportBtn);
        document.body.appendChild(floatingPanel);

        countSpan = document.getElementById('tm-bulk-count');
        manageFloatingPanelsVisibility();
    }

    function updateFloatingPanel() {
        initFloatingPanel();
        manageFloatingPanelsVisibility();
        if (countSpan) {
            countSpan.textContent = document.querySelectorAll('.tm-select-cb:checked').length;
        }
    }

    async function handleMultiExport() {
        const checkboxes = document.querySelectorAll('.tm-select-cb:checked');
        if (checkboxes.length === 0) return;

        exportBtn.disabled = true;
        const originalText = exportBtn.innerHTML;
        let items = [];

        for (let i = 0; i < checkboxes.length; i++) {
            exportBtn.innerHTML = `Processing... (${i + 1}/${checkboxes.length})`;

            const block = checkboxes[i].closest('li');
            const jpElement = block.querySelector('.bp-ddw') || block;
            const enElement = block.querySelector('.bp-sdw');

            items.push({
                cleanJP: getCleanJapanese(jpElement),
                cleanEN: getCleanEnglish(enElement),
                audioUrl: getAudioUrlForBlock(block),
                fileName: `bunpro_multi_${getSafeId()}_${i}.mp3`
            });
        }

        exportBtn.innerHTML = `Sending to Anki...`;
        const success = await sendToAnki(items);

        if (success) {
            exportBtn.innerHTML = "Sent to Anki!";
            exportBtn.style.background = "#43A047";
            checkboxes.forEach(cb => cb.checked = false);
        } else {
            exportBtn.innerHTML = "Anki Error!";
            exportBtn.style.background = "#E53935";
        }

        setTimeout(() => {
            exportBtn.innerHTML = originalText;
            exportBtn.style.background = "";
            exportBtn.disabled = false;
            updateFloatingPanel();
        }, 3000);
    }

    async function handleBulkExport(button, blocks) {
        if (!blocks || blocks.length === 0) return;

        button.disabled = true;
        const originalText = button.innerHTML;
        let items = [];
        const count = Math.min(blocks.length, 5);

        for (let i = 0; i < count; i++) {
            button.innerHTML = `Processing... (${i + 1}/${count})`;

            const block = blocks[i];
            const jpElement = block.querySelector('.bp-ddw') || block;
            const enElement = block.querySelector('.bp-sdw');

            items.push({
                cleanJP: getCleanJapanese(jpElement),
                cleanEN: getCleanEnglish(enElement),
                audioUrl: getAudioUrlForBlock(block),
                fileName: `bunpro_bulk_${getSafeId()}_${i}.mp3`
            });
        }

        button.innerHTML = `Sending to Anki...`;
        const success = await sendToAnki(items);

        if (success) {
            button.classList.add('success');
            button.innerHTML = "Sent 5 to Anki!";
        } else {
            button.classList.add('error');
            button.innerHTML = "Anki Error!";
        }
        setTimeout(() => {
            button.classList.remove('success', 'error');
            button.innerHTML = originalText;
            button.disabled = false;
        }, 3000);
    }

    function getFullKanaReading(element) {
        let kana = "";
        for (let node of element.childNodes) {
            if (node.nodeType === Node.TEXT_NODE) kana += node.textContent;
            else if (node.nodeName.toLowerCase() === 'ruby') {
                const rt = node.querySelector('rt');
                if (rt) kana += rt.textContent;
                else kana += node.textContent;
            } else {
                kana += getFullKanaReading(node);
            }
        }
        return kana;
    }

    function smartSplitMeanings(text) {
        const result = [];
        let current = '';
        let depth = 0;

        for (let i = 0; i < text.length; i++) {
            const char = text[i];
            if (char === '(' || char === '（' || char === '[' || char === '［') depth++;
            else if (char === ')' || char === '）' || char === ']' || char === '］') depth = Math.max(0, depth - 1);

            if ((char === ',' || char === '、') && depth === 0) {
                result.push(current.trim());
                current = '';
            } else {
                current += char;
            }
        }
        if (current.trim()) result.push(current.trim());
        return result;
    }

    function scanAndAddVocabTools() {
        const headerContainer = document.querySelector('h1[id^="rev-id-"]');
        if (!headerContainer) return;

        const currentId = headerContainer.id;
        if (headerContainer.dataset.tmVocabId !== currentId) {
            headerContainer.querySelectorAll('.tm-always-visible, .tm-vocab-meanings-container').forEach(el => el.remove());
            headerContainer.dataset.tmVocabId = currentId;

            let fullKana = "";
            const ddw = headerContainer.querySelector('.bp-ddw');
            if (ddw) fullKana = getFullKanaReading(ddw).trim();
            headerContainer.dataset.fullKana = fullKana; // Save for meanings to access later
        }

        const currentKana = headerContainer.dataset.fullKana || "";

        const dictBlocks = document.querySelectorAll('div[id^="jmdict-id-"] li.flex.items-start > div');
        dictBlocks.forEach(container => {
            if (container.dataset.tmDictProcessed === "true") return;
            container.dataset.tmDictProcessed = "true";

            const paragraphs = Array.from(container.children).filter(el => el.tagName.toLowerCase() === 'p');
            if (paragraphs.length === 0) return;

            const p = paragraphs[0];
            const rawText = p.textContent;

            const meanings = smartSplitMeanings(rawText).filter(s => s);

            if (meanings.length > 0) {
                p.style.display = 'none';

                const meaningsContainer = document.createElement('div');
                meaningsContainer.className = 'tm-vocab-meanings-container';
                meaningsContainer.style.justifyContent = 'flex-start';
                meaningsContainer.style.marginTop = '4px';

                meanings.forEach(m => {
                    const btn = document.createElement('button');
                    btn.className = 'tm-vocab-meaning-btn';
                    btn.innerHTML = `${ankiIcon} ${m}`; // Icon + text to indicate it sends to Anki
                    btn.onclick = (e) => { 
                        e.preventDefault(); 
                        e.stopPropagation(); 
                        sendVocabToAnki(m, currentKana, btn);
                    };
                    meaningsContainer.appendChild(btn);
                });
                container.insertBefore(meaningsContainer, p.nextSibling);
            }
        });
    }

    function getCleanQuizJapanese(quizSection) {
        if (!quizSection) return "";
        const clozeWrapper = quizSection.querySelector('.bp-quiz-question .text-center') || 
                             quizSection.querySelector('.bp-quiz-question') || 
                             quizSection.querySelector('[class*="QuestionSentenceQuestionCloze"]') || 
                             quizSection;
        
        let htmlParts = [];
        Array.from(clozeWrapper.childNodes).forEach(node => {
            if (node.nodeType === Node.TEXT_NODE) {
                const txt = node.textContent.trim();
                if (txt) htmlParts.push(txt);
            } else if (node.nodeType === Node.ELEMENT_NODE) {
                if (node.tagName.toLowerCase() === 'button' || node.classList.contains('bp-quiz-tense') || node.querySelector('input') || node.tagName.toLowerCase() === 'input') {
                    const inputEl = node.tagName.toLowerCase() === 'input' ? node : node.querySelector('input');
                    let answerText = "";
                    if (inputEl && inputEl.value && inputEl.value.trim()) {
                        answerText = inputEl.value.trim();
                    } else {
                        const clone = node.cloneNode(true);
                        clone.querySelectorAll('.bp-quiz-tense').forEach(t => t.remove());
                        clone.querySelectorAll('rp').forEach(rp => rp.remove());
                        const textContent = clone.textContent.trim();
                        if (textContent && textContent !== '____') {
                            const allElements = clone.getElementsByTagName("*");
                            for (let i = 0; i < allElements.length; i++) {
                                while (allElements[i].attributes.length > 0) allElements[i].removeAttribute(allElements[i].attributes[0].name);
                            }
                            answerText = clone.innerHTML.trim();
                        }
                    }
                    
                    if (answerText) {
                        htmlParts.push(`<span><span>${answerText}</span></span>`);
                    } else {
                        htmlParts.push(`<span><span>____</span></span>`);
                    }
                } else if (node.classList.contains('bp-ddw') || node.querySelector('ruby') || node.tagName.toLowerCase() === 'ruby' || node.tagName.toLowerCase() === 'span') {
                    const clone = node.cloneNode(true);
                    clone.querySelectorAll('rp').forEach(rp => rp.remove());
                    const allElements = clone.getElementsByTagName("*");
                    for (let i = 0; i < allElements.length; i++) {
                        while (allElements[i].attributes.length > 0) allElements[i].removeAttribute(allElements[i].attributes[0].name);
                    }
                    htmlParts.push(clone.innerHTML.trim());
                }
            }
        });
        
        let fullHtml = htmlParts.join("");
        if (!fullHtml) {
            fullHtml = getCleanJapanese(clozeWrapper);
        }
        
        fullHtml = fullHtml.replace(/\s{2,}/g, ' ').trim();
        fullHtml = fullHtml.replace(/\s+([。、！？.,!?])/g, '$1');
        return fullHtml.replace(/;/g, ',').replace(/\n/g, ' ');
    }

    function getCleanQuizEnglish(quizSection) {
        if (!quizSection) return "";
        const enElement = quizSection.querySelector('.bp-quiz-trans:not(.bp-quiz-trans--hint)') || 
                          quizSection.querySelector('.bp-quiz-trans-wrap .bp-sdw:not(.bp-quiz-trans--hint)') ||
                          quizSection.querySelector('.bp-quiz-trans-wrap .bp-sdw') ||
                          quizSection.querySelector('.bp-sdw');
        return getCleanEnglish(enElement);
    }

    function getAudioUrlForQuiz(quizSection, cleanJp) {
        extractAudioData();
        
        const source = quizSection.querySelector('audio source') || document.querySelector('#quiz audio source');
        if (source && source.getAttribute('src')) return makeAbsoluteUrl(source.getAttribute('src'));
        
        const audio = quizSection.querySelector('audio') || document.querySelector('#quiz audio');
        if (audio && audio.getAttribute('src')) return makeAbsoluteUrl(audio.getAttribute('src'));
        
        if (cleanJp) {
            let plainJp = cleanJp.replace(/<[^>]*>?/gm, '').replace(/[^\p{L}\p{N}]/gu, '');
            if (audioMap[plainJp]) return audioMap[plainJp];
        }
        
        const qIdMatch = quizSection.id && quizSection.id.match(/\d+/);
        if (qIdMatch && audioMap[qIdMatch[0]]) return audioMap[qIdMatch[0]];
        
        if (cleanJp) {
            let rawJp = cleanJp.replace(/<[^>]*>?/gm, '').trim();
            if (rawJp) return `https://dk3kgylsgq3k1.cloudfront.net/audio/vocab/tts/${encodeURIComponent(rawJp)}-male.mp3`;
        }
        return null;
    }

    function scanAndAddQuizTools() {
        try {
            const clozeWrapper = document.querySelector('.bp-quiz-question') || 
                                 document.querySelector('[class*="QuestionSentenceQuestionCloze"]') ||
                                 document.getElementById('js-tour-quiz-question');
            if (!clozeWrapper) return;

            const quizSection = clozeWrapper.closest('section') || clozeWrapper.parentElement || clozeWrapper;

            const currentText = clozeWrapper.textContent.trim();
            const existing = document.querySelector('.tm-quiz-anki-container');

            if (existing) {
                if (clozeWrapper.dataset.tmQuizProcessedText === currentText) {
                    return;
                }
                existing.remove();
            }
            clozeWrapper.dataset.tmQuizProcessedText = currentText;

            const container = document.createElement('div');
            container.className = 'tm-anki-btn-container tm-always-visible tm-quiz-anki-container';
            container.style.cssText = 'display: flex !important; justify-content: center !important; align-items: center !important; gap: 8px !important; margin: 12px 0 !important; width: 100% !important; z-index: 9999 !important; opacity: 1 !important; visibility: visible !important;';

            const btnJP = document.createElement('button');
            btnJP.className = 'tm-anki-btn';
            btnJP.style.cssText = 'background: #2b2d3a !important; color: #ffffff !important; border: 1px solid #4a4d62 !important; border-radius: 9999px !important; padding: 6px 14px !important; font-size: 13px !important; font-weight: 600 !important; cursor: pointer !important; display: inline-flex !important; align-items: center !important; gap: 6px !important; box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;';
            btnJP.innerHTML = `${copyIcon} JP`;
            btnJP.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                const cleanJP = getCleanQuizJapanese(quizSection);
                if (cleanJP) {
                    GM_setClipboard(cleanJP, 'text');
                    btnJP.innerHTML = "Copied!";
                    setTimeout(() => { btnJP.innerHTML = `${copyIcon} JP`; }, 1500);
                }
            };

            const btnEN = document.createElement('button');
            btnEN.className = 'tm-anki-btn';
            btnEN.style.cssText = 'background: #2b2d3a !important; color: #ffffff !important; border: 1px solid #4a4d62 !important; border-radius: 9999px !important; padding: 6px 14px !important; font-size: 13px !important; font-weight: 600 !important; cursor: pointer !important; display: inline-flex !important; align-items: center !important; gap: 6px !important; box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;';
            btnEN.innerHTML = `${copyIcon} EN`;
            btnEN.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                const cleanEN = getCleanQuizEnglish(quizSection);
                if (cleanEN) {
                    GM_setClipboard(cleanEN, 'text');
                    btnEN.innerHTML = "Copied!";
                    setTimeout(() => { btnEN.innerHTML = `${copyIcon} EN`; }, 1500);
                }
            };

            const btnAnki = document.createElement('button');
            btnAnki.className = 'tm-anki-btn';
            btnAnki.style.cssText = 'background: #2563eb !important; color: #ffffff !important; border: 1px solid #3b82f6 !important; border-radius: 9999px !important; padding: 6px 14px !important; font-size: 13px !important; font-weight: 600 !important; cursor: pointer !important; display: inline-flex !important; align-items: center !important; gap: 6px !important; box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;';
            btnAnki.innerHTML = `${ankiIcon} Copy to Anki`;
            btnAnki.onclick = async (e) => {
                e.preventDefault();
                e.stopPropagation();
                btnAnki.innerHTML = "...";
                btnAnki.disabled = true;

                const cleanJP = getCleanQuizJapanese(quizSection);
                const cleanEN = getCleanQuizEnglish(quizSection);
                const audioUrl = getAudioUrlForQuiz(quizSection, cleanJP);

                let items = [{
                    deckName: ANKI_REVIEW_DECK_NAME,
                    modelName: ANKI_MODEL_NAME,
                    mainField: "Japanese",
                    cleanJP: cleanJP,
                    cleanEN: cleanEN,
                    audioUrl: audioUrl,
                    fileName: `bunpro_review_${getSafeId()}.mp3`
                }];

                if (await sendToAnki(items)) {
                    btnAnki.style.background = "#16a34a !important";
                    btnAnki.innerHTML = "Sent to Anki!";
                } else {
                    btnAnki.style.background = "#dc2626 !important";
                    btnAnki.innerHTML = "Error";
                }

                setTimeout(() => {
                    btnAnki.style.background = "#2563eb !important";
                    btnAnki.innerHTML = `${ankiIcon} Copy to Anki`;
                    btnAnki.disabled = false;
                }, 2000);
            };

            container.appendChild(btnJP);
            container.appendChild(btnEN);
            container.appendChild(btnAnki);

            const transWrap = document.querySelector('.bp-quiz-trans-wrap') || quizSection.querySelector('.bp-quiz-trans-wrap');
            if (transWrap && transWrap.parentNode) {
                transWrap.parentNode.insertBefore(container, transWrap);
            } else if (clozeWrapper.nextSibling) {
                clozeWrapper.parentNode.insertBefore(container, clozeWrapper.nextSibling);
            } else if (clozeWrapper.parentNode) {
                clozeWrapper.parentNode.appendChild(container);
            } else {
                quizSection.appendChild(container);
            }
        } catch (err) {
            console.error("[Bunpro Anki] scanAndAddQuizTools error:", err);
        }
    }

    function scanAndAdd() {
        try { scanAndAddLibraryTools(); } catch(e) {}
        try { scanAndAddVocabTools(); } catch(e) {}
        try { scanAndAddQuizTools(); } catch(e) {}

        const examplesHeader = document.getElementById('examples');
        if (!examplesHeader) return;

        const examplesWrapper = examplesHeader.parentElement;
        if (!examplesWrapper) return;

        const studyBlocks = Array.from(examplesWrapper.querySelectorAll('li[id^="study-question-"]'));
        if (studyBlocks.length === 0) return;

        initFloatingPanel();

        const examplesList = examplesWrapper.querySelector('ul');
        if (examplesList) {
            let wrapper = examplesList.previousElementSibling;
            if (!wrapper || !wrapper.classList.contains('tm-bulk-btn-wrapper')) {
                wrapper = document.createElement('div');
                wrapper.className = 'tm-bulk-btn-wrapper';
                const bulkBtn = document.createElement('button');
                bulkBtn.className = 'tm-floating-btn tm-bulk-btn';
                bulkBtn.innerHTML = `${ankiIcon} Bulk Send Top 5 to Anki`;
                bulkBtn.onclick = () => handleBulkExport(bulkBtn, studyBlocks);
                wrapper.appendChild(bulkBtn);
                examplesList.parentNode.insertBefore(wrapper, examplesList);
            }
        }

        studyBlocks.forEach(block => {
            const currentBlockId = block.id;
            if (block.dataset.tmProcessedId === currentBlockId) return;

            block.querySelectorAll('.tm-select-cb, .tm-anki-btn-container').forEach(el => el.remove());
            block.dataset.tmProcessedId = currentBlockId;

            if (getComputedStyle(block).position === 'static') {
                block.style.position = 'relative';
            }

            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.className = 'tm-select-cb';
            cb.style.cssText = 'position:absolute; top:12px; right:12px; width:20px; height:20px; cursor:pointer; z-index:99; accent-color:rgb(var(--c-primary-accent));';
            cb.addEventListener('change', updateFloatingPanel);
            block.appendChild(cb);

            const jpElement = block.querySelector('.bp-ddw');
            const enElement = block.querySelector('.bp-sdw');
            if (jpElement && enElement) {
                const container = document.createElement('div');
                container.className = 'tm-anki-btn-container';

                const btnJP = document.createElement('button');
                btnJP.className = 'tm-anki-btn';
                btnJP.innerHTML = `${copyIcon} JP`;
                btnJP.onclick = (e) => { e.preventDefault(); e.stopPropagation(); GM_setClipboard(getCleanJapanese(jpElement), 'text'); };

                const btnEN = document.createElement('button');
                btnEN.className = 'tm-anki-btn';
                btnEN.innerHTML = `${copyIcon} EN`;
                btnEN.onclick = (e) => { e.preventDefault(); e.stopPropagation(); GM_setClipboard(getCleanEnglish(enElement), 'text'); };

                const btnAnki = document.createElement('button');
                btnAnki.className = 'tm-anki-btn';
                btnAnki.innerHTML = `${ankiIcon} Send to Anki`;
                btnAnki.onclick = async (e) => {
                    e.preventDefault(); e.stopPropagation();
                    const audioUrl = getAudioUrlForBlock(block);
                    
                    btnAnki.innerHTML = "...";
                    let items = [{
                        cleanJP: getCleanJapanese(jpElement),
                        cleanEN: getCleanEnglish(enElement),
                        audioUrl: audioUrl,
                        fileName: `bunpro_single_${getSafeId()}.mp3`
                    }];

                    if (await sendToAnki(items)) {
                        btnAnki.classList.add('success');
                        btnAnki.innerHTML = "Sent!";
                    } else {
                        btnAnki.classList.add('error');
                        btnAnki.innerHTML = "Error";
                    }
                    setTimeout(()=> { btnAnki.classList.remove('success', 'error'); btnAnki.innerHTML = `${ankiIcon} Send to Anki`;}, 2000);
                };

                container.appendChild(btnJP);
                container.appendChild(btnEN);
                container.appendChild(btnAnki);
                jpElement.parentNode.insertBefore(container, jpElement);
            }
        });

        manageFloatingPanelsVisibility();
    }

    // 1. Run immediately on execution
    scanAndAdd();

    // 2. Start DOM Mutation Observer
    const observer = new MutationObserver(() => scanAndAdd());
    observer.observe(document.body, { childList: true, subtree: true });

    // 3. Fallback periodic check every 400ms for fast Single-Page-App quiz transitions
    setInterval(() => scanAndAdd(), 400);

    // 4. Asynchronously sync VPS copied items without blocking UI
    loadCopiedItems().then(() => {
        scanAndAdd();
    });

})();
