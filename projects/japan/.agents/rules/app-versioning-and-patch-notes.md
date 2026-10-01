# Mandatory App Versioning & Patch Notes Invariant

## Overview
Ogni modifica al codice dell'applicazione (frontend, backend, API), alla pipeline di sincronizzazione, o alla struttura/dati del database (SQLite, Anki, Bunpro) impone tassativamente l'aggiornamento formale della versione dell'app e la redazione delle relative note di rilascio (patch notes).

## Strict Invariants

1. **Incremento di Versione Obbligatorio su Ogni Modifica**:
   - È severamente vietato applicare modifiche funzionali, correzioni di bug o aggiornamenti a database/mazzi senza incrementare la versione dell'applicazione (Semantic Versioning: `v2.x.x` / build timestamp).
   - L'allineamento deve avvenire in modo atomico su tutti i punti canonici di controllo:
     1. `static/js/modules/anki_web_updater.js`: `CURRENT_VERSION` e `CURRENT_BUILD`.
     2. `api/routes/anki_web_routes.py`: endpoint `GET /api/anki/version` (`version`, `build`, `release_date`).
     3. `sw_anki.js` e `static/sw_anki.js`: incremento di `CACHE_NAME` (es. `anki-pwa-vXX`) per forzare l'invalidazione della cache PWA su mobile/Redmi Note 7.
     4. `templates/anki.html`: aggiornamento del query parameter di cache-busting sul bundle (es. `anki_bundle.js?v=...`).

2. **Patch Notes e Changelog Dettagliati**:
   - Ogni rilascio deve includere una voce descrittiva chiara in italiano all'inizio dell'array `changelog` in `api/routes/anki_web_routes.py`.
   - La nota deve sintetizzare:
     - Il problema risolto alla radice (es. estrazione multi-lettura, disambiguazione contesto).
     - Il beneficio pratico visibile per lo studio dell'utente.
   - La voce deve essere contestualmente archiviata nel registro storico in `research/registro_proattivo_rischi_e_soluzioni_mext.md`.

3. **Zero Rilasci Silenti**:
   - Nessun client deve ricevere codice o dati modificati mantenendo la vecchia etichetta di versione. L'utente deve sempre poter verificare a colpo d'occhio nel cockpit o nel modale OTA quale build è attualmente in esecuzione.
