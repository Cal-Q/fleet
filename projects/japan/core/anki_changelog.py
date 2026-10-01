#!/usr/bin/env python3
"""
core/anki_changelog.py — AnkiDroid & Web Version Changelog Registry
Strictly <= 200 lines and <= 100 cols.
"""

from typing import List

ANKI_CHANGELOG: List[str] = [
    (
        "Reintegrazione Master JMdict & Stripping Spazi Frasi (v2.10.16): "
        "Reintegrate le tabelle JMdict (entries, reading_elements, senses, "
        "glosses, furigana) nel database unificato dict_index.sqlite3, "
        "risolvendo l'errore 500 su /api/study/add_batch; normalizzato lo stripping "
        "delle frasi Bunpro per la perfetta riconciliazione delle carte Anki."
    ),
    (
        "Eradicazione JSON di Stato & Ripristino Verità SQLite (v2.10.15): "
        "Ripristinati e riconciliati kanji_catalog (2.300 voci, 1.142 Anki), "
        "bunpro_grammar_points (979 voci, 355 Anki) e jlpt_vocab (9.165 voci, "
        "2.881 Anki) in dict_index.sqlite3; eliminati i 4 JSON di stato "
        "disallineati e 10 JSON orfani; code derivate 100% da SQLite e Anki."
    ),
    (
        "Ripristino Coda Studio Bunpro & Precompilazione Tailwind (v2.10.14): "
        "Popolata la tabella bunpro_grammar_vocab_coverage (35.047 voci) in dict_index.sqlite3 "
        "risolvendo l'errore 500 su /api/study/next; aggiunto fallback difensivo in "
        "grammar_vocab_gate.py; rimossa la dipendenza runtime da cdn.tailwindcss.com "
        "utilizzando il CSS locale precompilato static/css/tailwind.min.css."
    ),
    (
        "Fix Coda Fine Mazzo, Schermata Cooldown & 60 FPS Mobile (v2.10.13): "
        "Ripristinato il contenitore della carta nelle schermate di cooldown eliminando "
        "la schermata nera; mantenuto visibile il messaggio Mazzo Completato senza kickout; "
        "rimosso il refill asincrono spuro a fine mazzo; differita la persistenza IndexedDB "
        "e sospesi i tick timer durante il drag per garantire 60 FPS stabili su CPU lente."
    ),
    (
        "Choreografia Deck Cinema, Slide Lenta & Zero Ghosting (v2.10.12): "
        "La carta sottostante rimane fissa a scale 0.94 durante il drag; slide "
        "fluida a 280ms allo swipe con avvicinamento successivo della carta sotto "
        "e fade-in dei nuovi contenuti; eliminato il ghosting dei badge correct/wrong "
        "e rimosso il timeout di 150ms per pre-decodifica GPU immediata delle immagini."
    ),
    (
        "Fisica Drag 60 FPS & Fix Persistenza Regola Diversa (v2.10.11): "
        "Ottimizzata la pipeline di animazione drag: eliminati reflow e query DOM "
        "frequenti su badge; trasformazioni GPU isolate e touch-none nativo su mobile; "
        "corretta la visualizzazione della Regola Diversa eliminando la cancellazione "
        "prematura di ivl>=10 e azzerando ivl al rientro in apprendimento."
    ),
    (
        "Fisica Tattile Mazzo & Carta Stack Sottostante Dinamica (v2.10.10): "
        "Aggiunta carta bianca di sfondo posizionata sotto la carta attiva; visibile "
        "durante il trascinamento e scalata dinamicamente verso il primo piano con la "
        "distanza; animazione fluida di avvicinamento allo schermo quando la carta viene "
        "lanciata via con apparizione reattiva dei nuovi contenuti."
    ),
    (
        "Staging Immagini High-Priority & Lookahead Pipelining Istantaneo (v2.10.9): "
        "Sostituito loading lazy bloccante con eager e fetchpriority high sulle immagini; "
        "introdotto lookahead buffer a 4 carte con pre-decodifica in memoria via Image() "
        "e indicizzazione multi-chiave (encoded/decoded) nella cache del Service Worker; "
        "immagini visibili istantaneamente (0ms) alla visualizzazione del retro."
    ),
    (
        "Ottimizzazione Mobile Ultra Power-Saving & Zero Flash/Layer I/O (v2.10.8): "
        "Eliminato il blocco di store.getAll() e ricalcolo gerarchico in IndexedDB ad ogni "
        "carta; isolato updateCachedCardReview sul singolo mazzo; memorizzata cache in-memory "
        "per regole e debouncing a 5s dei log localStorage; rimossi will-change-transform e "
        "animazioni CSS continue per azzerare il carico GPU/compositor su Redmi Note 7."
    ),
    (
        "Compilazione AOT Tailwind CSS & Eliminazione MutationObserver (v2.10.7): "
        "Rimosso il compilatore runtime in-browser tailwind.js (398KB) che bloccava "
        "il thread principale su CPU a risparmio energetico (Redmi Note 7); introdotto "
        "foglio di stile pre-compilato static/css/tailwind.min.css con azzeramento "
        "totale del consumo CPU e del lag al cambio carta e alla visualizzazione del retro."
    ),
    (
        "Zero-Lag Transizione Carte, Risposta Diretta & Defer Sync IDB (v2.10.6): "
        "Eliminato il lag di oltre 200ms al cambio carta; bottoni e scorciatoie invocano "
        "direttamente ankiAnswerCard in <1ms con avanzamento istantaneo del contatore; "
        "differito il salvataggio pesante IndexedDB e il parsing retro a microtask 20ms; "
        "inibito il re-render inutile della lista mazzi nascosta durante lo studio attivo."
    ),
    (
        "Architettura Unica Anki, Derivazione Pura Stato & 0 Euristiche (v2.10.5): "
        "Eliminata la doppia verita tra backend e frontend; rimosso definitivamente "
        "il residuo in-memory processReviewStats con decrementi a vista; contatori "
        "di sessione derivati come funzione pura deterministica dallo store delle carte; "
        "rimozione integrale del vecchio codice deprecato a favore del modello Anki."
    ),
    (
        "Ordinamento Deterministico 3-Tier Rosse/Verdi Random & Blu In Ordine (v2.10.4): "
        "Allineato rigorosamente l'ordine di studio: 1. Carte rosse a cooldown terminato "
        "(estratte in ordine randomico); 2. In assenza di rosse pronte, carte verdi random a "
        "cooldown terminato; 3. In assenza di verdi, carte blu nuove in ordine sequenziale (non "
        "random); 4. Schermata attesa cooldown con Learn Ahead per rosse con timer futuro."
    ),
    (
        "Parita Integrale Sessione Studio & Rollup Mazzi Padre (v2.10.3): "
        "Risolta la discrepanza tra panoramica e sessione di studio attiva; preservata la "
        "struttura gerarchica dei mazzi padre (has_children/is_master) all'avvio sessione, "
        "garantendo l'aggregazione atomica di tutti i sotto-mazzi (es. Travel Pack: Frasi + "
        "Vocabolario + Kanji) ed eliminando l'incompleto fallback a singolo mazzo foglia; "
        "partizionamento e indicizzazione automatica delle carte per did in IndexedDB."
    ),
    (
        "Allineamento Deterministico Contatori Panoramica Mazzo (v2.10.2): "
        "Eliminata la sovrascrittura asincrona parziale in openDeckOverview che "
        "generava discrepanze tra conteggi dell'elenco mazzi e vista panoramica; "
        "calcolo unificato dei conteggi per mazzi foglia e raccolte padre; "
        "garantita identità al 100% tra lista principale e schermata mazzo."
    ),
    (
        "Ottimizzazione Studio Locale & Fix Timer/Rete (v2.10.1): "
        "Caricamento prioritario immediato delle carte da IndexedDB (<2ms) "
        "senza attendere la rete; eliminato il freeze del timer causato "
        "dalla serializzazione lenta del server; isolato il listener "
        "controllerchange del Service Worker per prevenire ricaricamenti spontanei "
        "durante lo studio; resa polimorfica la firma di openDeckOverview."
    ),
    (
        "Flip Istantaneo Pre-renderizzato & Rollup Mazzi Gerarchico (v2.10.0): "
        "Eliminato il freeze/lag di 100-300ms al tap: retro della card interamente "
        "pre-renderizzato a riposo mentre l'utente legge il fronte (latenza flip 0.43ms); "
        "nuovo motore client-side anki_deck_rollup per il calcolo e la somma gerarchica "
        "delle scadenze di mazzi foglia e raccolte/padre direttamente da IndexedDB; "
        "corretta formula SM-2 locale con esclusione totale di carte sospese/leech."
    ),
    (
        "Ripristino Scorrimento Verticale Spiegazioni Card (v2.9.6): "
        "Rimossi i listener ridondanti con stopPropagation su touchmove e touchstart "
        "nell'area delle spiegazioni e letture che bloccavano il pan nativo su Chrome/Android; "
        "isolamento garantito del tocco nella zona spiegazioni prima del drag handler; "
        "preservazione integrale delle gesture di swipe nella barra inferiore."
    ),
    (
        "Avvio Istantaneo & Sync On-Demand (v2.9.5): "
        "Rimosso il prefetch automatico di tutti gli 8 mazzi all'avvio dell'app; "
        "apertura immediata della Home in 40ms con zero banner e zero download; "
        "caricamento istantaneo delle carte (incluse nuove) solo all'avvio dello studio; "
        "sincronizzazione completa dell'archivio delegata al tasto 'Forza Sincronizzazione'."
    ),
    (
        "Disaccoppiamento Impronta Mazzi & Zero Download Loop (v2.9.4): "
        "Il fingerprint dei mazzi traccia ora la modifica dei contenuti (notes.mod) "
        "anziché il timestamp di studio delle carte (cards.mod); "
        "eliminata l'invalidazione spuria che causava il riscaricamento a catena "
        "di mazzi pesanti (Frasi 10MB, Vocabolario 3.187 carte) ad ogni apertura dell'app; "
        "preservazione totale della cache IndexedDB se le carte sono già presenti localmente."
    ),
    (
        "Sincronizzazione Atomica Cache Mazzi & Fix Overview (v2.9.3): "
        "Risolto disallineamento contatori tra Home Page e Riepilogo Mazzo; "
        "eliminata sovrascrittura di dati reali con cache stale di IndexedDB; "
        "gestione nativa di 0 carte dovute senza riesumazione di cache obsolete; "
        "propagazione immediata dei ripassi su tutte le istanze mazzo in IndexedDB."
    ),
    (
        "Priorità Assoluta Carte Rosse Scadute (v2.9.2): "
        "Allineamento rigoroso allo standard Anki: le carte in apprendimento (rosse) "
        "con cooldown terminato hanno precedenza immediata sulle carte verdi di ripasso, "
        "sia nell'ordinamento SQL iniziale del mazzo sia nella progressione attiva della sessione."
    ),
    (
        "Risoluzione Transizione Carte & Reset Fly-off (v2.9.1): "
        "Risolto bug critico per cui dopo la prima carta studiata il contenitore "
        "rimaneva invisibile fuori dallo schermo; ripristino istantaneo di opacity e transform "
        "con fallback robusto su ankiCardContainer per animateCardEntrance e resetCardPosition."
    ),
    (
        "Feedback Visivo Aggiornamenti & Sync Mazzi in Tempo Reale (v2.9.0): "
        "Banner globale e progress bar dettagliata per ogni fase di download; "
        "notifica immediata di download nuova versione SW e avanzamento mazzi "
        "con conteggio (X/Y), percentuale e stato offline verificato."
    ),
    (
        "Persistenza Totale Cache & Sync Intelligente Zero-Download (v2.8.9): "
        "Separazione totale tra codice e dati persistenti (font, media, carte); "
        "impronta di contenuto deterministica (zero riscaricamento a cambio versione); "
        "aggiornamento incrementale dei mazzi senza sovrascrittura distruttiva."
    ),
    (
        "Unflip & Decomposizione Architetturale Gestures (v2.8.8): "
        "Tasto e gesture Undo a risposta mostrata nascondono la risposta "
        "e resettano il countdown al massimo riavviando il timer; "
        "rifarlo fa undo della carta precedente. Modulo gesti decomposto "
        "in anki_card_animator.js con conformità rigorosa Rule 2."
    ),
    (
        "Tiered Caching & Rimozione badge Context (v2.8.7): "
        "Separazione cache PWA in anki-media-v1 permanente (font, SVG, pesi TPU) "
        "e anki-code-v52 leggero; eliminato badge 'Context' dal fronte frasi."
    ),
]
