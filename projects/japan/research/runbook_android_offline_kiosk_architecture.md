# Runbook: Architettura Android Offline Kiosk & Sincronizzazione SRS

## 1. Visione d'Insieme & Obiettivo
L'applicazione Android Kiosk (`it.calq.japan`) garantisce lo studio continuo di Anki SRS su dispositivi mobili (es. Redmi Note 7, `lavender_eea`, Android 10) in modalità **100% offline**, con sincronizzazione bidirezionale trasparente verso il database centrale SQLite `collection.anki2` al ripristino della connettività.

---

## 2. Pipeline di Build Standalone (Zero Android Studio Overhead)
L'APK viene generato tramite lo script [`scripts/build_kiosk_apk.sh`](file:///mnt/workspaces/japan/scripts/build_kiosk_apk.sh) utilizzando la toolchain nativa a riga di comando (AAPT, ECJ, DX, APKSigner):

1. **Compilazione Bundle Client**:
   ESBuild compila i moduli modulari ($\le 200$ righe) in un singolo bundle atomico:
   ```bash
   npx esbuild static/js/modules/anki_main.js --bundle --format=iife --outfile=static/js/anki_bundle.js
   ```
2. **Impacchettamento Asset Statici**:
   `anki.html`, `anki_bundle.js` e `tailwind.js` vengono copiati direttamente dentro `assets/` dell'APK.
3. **Compilazione Bytecode Java**:
   `ecj` compila [`MainActivity.java`](file:///mnt/workspaces/japan/scripts/build_kiosk_apk.sh) contro `android.jar` (API 29).
4. **DEX & Firma APK**:
   `dx` genera `classes.dex`, `aapt` assembla il pacchetto e `apksigner` firma con keystore locale dedicato.

---

## 3. Architettura WebView & Intercettazione Richieste (`shouldInterceptRequest`)
Per prevenire errori `net::ERR_INTERNET_DISCONNECTED` e conservare l'origine sicura `https://japan.calq.it`:

- **Conservazione Origine**: L'app carica inizialmente l'URL `https://japan.calq.it/anki`. In questo modo `window.origin`, cookie di sessione, LocalStorage e IndexedDB rimangono perfettamente allineati tra versione web e versione kiosk.
- **Intercettazione Trasparente**:
  ```java
  public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest req) {
      String path = req.getUrl().getPath();
      if (path.equals("/anki") || path.equals("/anki/")) return loadAsset("anki.html", "text/html");
      if (path.endsWith("anki_bundle.js")) return loadAsset("anki_bundle.js", "application/javascript");
      if (path.endsWith("tailwind.js")) return loadAsset("tailwind.js", "application/javascript");
      return null;
  }
  ```
- **Fallback JSON Statico**: In `anki.html`, i dati iniziali Jinja2 sono serializzati in `<script id="anki-initial-decks" type="application/json">`, consentendo al bundle JS di avviarsi offline leggendo direttamente da IndexedDB senza generare errori di parsing.

---

## 4. Motore Offline IndexedDB & Outbox Pattern
La persistenza locale e la sincronizzazione risiedono nel modulo [`anki_offline_store.js`](file:///mnt/workspaces/japan/static/js/modules/anki_offline_store.js):

1. **Snapshot Cache Mazzi & Carte**:
   Quando online, i dati SRS vengono salvati negli store IndexedDB `decks` e `cards`.
2. **Ripasso Offline & `review_outbox`**:
   Durante lo studio offline, ogni voto (1=Again, 2=Hard, 3=Good, 4=Easy) viene salvato nello store `review_outbox` con timestamp, tempo impiegato e stato della scheda.
3. **Flusso di Sincronizzazione al Rientro Online**:
   - All'evento `window.addEventListener('online')` o al tocco del pulsante *Sincronizza*, le recensioni pendenti vengono inviate in batch a `/api/anki/sync_offline_reviews`.
   - Il backend scrive atomicamente i record in `revlog` e aggiorna `cards` nel database SQLite `collection.anki2`.
   - Ad avvenuta conferma `200 OK`, l'outbox locale viene svuotato atomicamente.

---

## 5. Manutenzione, Debug ADB su Tunnel Inverso & Test Fisici
Il dispositivo mobile è ispezionabile da remoto tramite il tunnel SSH inverso su porta 2223:

```bash
# 1. Connessione ADB al telefono tramite relay Chromebook
adb connect 10.23.186.52:5555

# 2. Verifica pacchetto installato e permessi
adb shell pm list packages | grep calq.japan

# 3. Test isolamento offline (Toggle Wi-Fi / Dati)
adb shell svc wifi disable && adb shell svc data disable

# 4. Avvio applicazione Kiosk & Cattura Schermo
adb shell am start -n it.calq.japan/.MainActivity
adb exec-out screencap -p > /tmp/screen_kiosk.png
```

---

## 6. Sistema di Telemetria & Log Diagnostici Persistenti
Per permettere la tracciabilità e la riproduzione post-mortem dei bug anche a sessione persa o app chiusa:

1. **Ring-Buffer Circolare Locale (`static/js/modules/anki_logger.js`)**:
   - Mantiene in memoria e in `localStorage` gli ultimi 300 eventi strutturati (`time`, `level`, `cat`, `act`, `det`, `online`).
   - Intercetta automaticamente `window.onerror` e `window.onunhandledrejection`.
   - Categorie tracciate: `SYSTEM`, `NAV`, `DECK`, `CARD`, `CACHE`, `NET`, `ERROR`.
2. **Modal di Diagnostica UI Integrato (`static/js/modules/anki_log_viewer.js`)**:
   - Accessibile direttamente dal pulsante `📋` nella barra superiore di Anki.
   - Filtri per categoria (`ALL`, `DECK`, `CARD`, `NET`, `ERROR`) e campo di ricerca full-text in tempo reale.
   - Azioni rapide: *Copia JSON* negli appunti, *Invia al Server* e *Pulisci Registro*.
3. **Ingestione Server-Side Centralizzata (`api/routes/anki_log_routes.py`)**:
   - Endpoint `POST /api/anki/client_logs`: accetta batch di telemetria e li persiste atomicamente in `/opt/japan/logs/anki_client_telemetry.jsonl`.
   - Endpoint `GET /api/anki/client_logs`: permette l'ispezione immediata dei log remoti da CLI o web dashboard.

---

## 7. Isolamento Sessioni & Prevenzione Race Condition nei Mazzi
- **Monotonic Session Token (`_sessionToken`)**:
  Ogni apertura di mazzo o cambio vista incrementa `_sessionToken`. Tutte le risposte asincrone di riempimento carte (`checkAndRefillCards`) e chiamate di rete verificano che il token della promessa corrisponda alla sessione attiva. Risposte obsolete o arrivate in ritardo vengono scartate atomicamente, impedendo contaminazioni di carte tra mazzi diversi (es. tra *Travel Pack* e mazzi paralleli).
- **Normalizzazione Chiavi Deck ID (`Number(did)`)**:
  Previene disallineamenti di tipo string/number nelle query IndexedDB degli store mazzi e schede.

---

## 8. Resilienza Offline Reload & Persistenza Mazzi Multi-Tier (v2.5.2)
Per garantire che nessun mazzo o stile grafico venga mai rimosso o perso durante il reload offline:

1. **Multi-Tier Synchronous Cache Hierarchy (`static/js/modules/anki_web_decks.js`)**:
   - `getSyncDecks()` valuta in ordine: `window.__INITIAL_DECKS__` $\to$ `localStorage.getItem('anki_cached_decks')` $\to$ fallback vuoto.
   - All'avvio o a qualsiasi aggiornamento valido dei mazzi, la lista viene sincronizzata immediatamente in `localStorage` e salvata in IndexedDB (`cacheDecks()`).
   - `renderDecks()` non mostra mai *"Nessun mazzo trovato"* se una qualsiasi sorgente locale contiene i mazzi memorizzati.
2. **Protezione da Sovrascritture Vuote & Purge Selettivo (`static/js/modules/anki_web_db.js`)**:
   - `cacheDecks(decks)` implementa un guard rigido: array nulli, non-array o vuoti non sovrascrivono mai la cache esistente.
   - `clearCardCache()` pulisce unicamente `deck_cards`, conservando permanentemente la tabella `decks` nello store `meta`.
3. **Inizializzazione Consapevole della Connettività (`static/js/modules/anki_web_ui.js`)**:
   - L'aggiornamento della build ID (`localStorage.setItem('anki_ui_build', BUILD_ID)`) invoca `clearCardCache()` esclusivamente se `navigator.onLine` è attivo, prevenendo la cancellazione delle schede offline a dispositivo disconnesso.
4. **Pre-caching Asset Critici nel Service Worker (`static/sw_anki.js`)**:
   - `STATIC_ASSETS` include `/api/anki/decks`, `tailwind.js`, manifest e bundle.
   - L'intercettore fetch implementa fallback JSON sintetico e cache-first per i fogli di stile Tailwind, garantendo rendering perfetto a 120fps senza degradazione visiva anche a Wi-Fi disattivato.
5. **Rimozione del Redirect Distruttivo `onReceivedError` (`scripts/build_kiosk_apk.sh`)**:
   - WebView mantiene sempre l'origine sicura `https://japan.calq.it/anki` servita dagli asset locali interni, evitando la transizione a `file:///android_asset/anki.html` che causava la perdita di accesso a IndexedDB e LocalStorage.

