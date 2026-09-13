# Japan • Studies & Mastery (Road to MEXT FY2027)

Unified Japanese language mastery, Anki SRS engine, and MEXT scholarship qualification platform.
**Candidato**: Patrik Potenza (UniTO L-11 • Matricola 993141)  
**Obiettivo Strategico**: Vincere la borsa di studio MEXT Japanese Studies (*Nikken-sei*) — Ambasciata del Giappone a Roma.  
**Orizzonte Temporale**: 13 Settembre 2026 – 20 Febbraio 2027 (161 Giorni • ~140 min/giorno medi).

---

## 🧭 INVARIANTE CARDINE: CONSULTAZIONE CONTINUA & AGGIORNAMENTO BIVIVO

1. **Lettura Obbligatoria Preventiva ad Ogni Passo**:
   - Qualsiasi agente o processo DEVE consultare e rileggere la presente documentazione (`README.md`, [`AGENTS.md`](file:///mnt/workspaces/japan/AGENTS.md) e la cartella [`research/`](file:///mnt/workspaces/japan/research/)) ad ogni singolo passaggio prima di eseguire modifiche, per verificare l'aderenza assoluta a TUTTE le richieste storiche e scongiurare qualsiasi deriva o allucinazione metodologica.
2. **Aggiornamento Permanente di Ogni Cambiamento**:
   - Ogni variazione di paradigma, nuovo requisito, decisione didattica o contromisura tecnica DEVE essere immediatamente e permanentemente registrata nella documentazione repository e riflessa in modo speculare e intuitivo sul sito web live ([`https://japan.calq.it`](https://japan.calq.it)).
   - È vietato qualsiasi stato headless: ciò che vive nel backend o nella documentazione deve essere visibile e ispezionabile sulla console web.

---

## 📐 Specifiche di Studio & Invarianti Didattici

- **Grammar Gating (Vocab-First Comprehensible Input)**:
  Le regole grammaticali Bunpro in `/api/study/next` rimangono bloccate fino a quando tutti i vocaboli contenuti nelle rispettive frasi d'esempio non sono stati studiati ($\ge 1$ ripetizione in Anki), eliminando l'attrito di decodifica lessicale durante lo studio della sintassi.
- **Progressione Kanji Resiliente (5 nuovi/giorno)**:
  - **Patrimonio**: 1.105 kanji maturi (`reps > 0`), 1.204 residui.
  - **Fase 1 (Giorni 1–6)**: Chiusura integrale dei 30 kanji residui N5+N4 (7 N5 + 23 N4).
  - **Fase 2 (Giorni 7–56)**: Padronanza integrale dei 251 kanji N3 a supporto delle Sezioni A e B.
  - **Fase 3 (Giorni 57–160)**: Consolidamento selettivo N2/N1, raggiungendo ~1.850–1.900 caratteri prima dell'esame.
  - **Prioritizzazione Dinamica**: La coda privilegia prioritariamente i kanji presenti nei vocaboli delle imminenti regole grammaticali.
- **Protocollo Kintsugi per Carte Sanguisuga (*Leeches*)**:
  Le carte sospese ripetutamente da Anki (`cards.queue = -1`) non vengono abbandonate, ma riabilitate attivamente tramite il modulo [bunki.js](file:///mnt/workspaces/japan/static/js/modules/bunki.js) con scomposizione etimologica dei radicali.

---

## 🎯 Target Punteggio Esame MEXT & Struttura delle Prove

| Sezione | Livello JLPT | Punti Max | Target Minimo | Punteggio Atteso | Pacing Target |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Parte A** | N5 / N4 | 35 | 32 (91%) | **33–34 (94–97%)** | $\le 25$ secondi/quesito (max 15 min netti). |
| **Parte B** | N3 / N2 | 35 | 18 (51%) | **20–22 (57–63%)** | $\le 40$ secondi/quesito (max 20 min netti). |
| **Parte C** | N1 | 30 | 9 (30%) | **10–12 (33–40%)** | 20–22 min riservati alla lettura accademica. |
| **TOTALE** | — | **100** | **59%** | **63–68%** | **55 minuti operativi netti** (+5 min buffer OMR matita 2B). |

- **Banca Dati Drill Originale (235 Quesiti Inediti)**:
  - [`drill_pool_part_a.json`](file:///mnt/workspaces/japan/exams/drill_pool_part_a.json): **110 item** (particelle, coppie omofone, radicali simili).
  - [`drill_pool_part_b.json`](file:///mnt/workspaces/japan/exams/drill_pool_part_b.json): **75 item** (Keigo, causativo-passivo, composti, unscrambling $\bigstar$).
  - [`drill_pool_part_c.json`](file:///mnt/workspaces/japan/exams/drill_pool_part_c.json): **50 item** (letture accademiche sui Terzi Luoghi, formule scritte N1).
- **Simulatore Orale Ambasciata**:
  - [`interview_questions.json`](file:///mnt/workspaces/japan/academic/interview_questions.json): 10 scenari orali codificati con modelli Keigo, metodologie di ricerca qualitativa (`参与観察`, `半構造化面接`, `言説分析`) e difesa della tesi.

---

## 🌐 Web Platform & Console Live (`https://japan.calq.it/`)

La web console è strutturata in 5 stage orizzontali navigabili a scorrimento fluido:
1. **日課 Routine**: Command center quotidiano con i 4 slot orari e i 23 giorni cuscinetto.
2. **学習 Studio**: Batch di studio guidato con sblocco progressivo kanji, vocaboli e grammatica.
3. **復習 Bunki**: Telemetria Anki SRS, verifica zero arretrati e riabilitazione leech.
4. **試練 Prove**: Motore d'esame a rotazione giornaliera con cronometro di pacing e simulatore orale.
5. **計画 Dossier**: Libretto universitario Esse3 UniTO, checklist bando Ambasciata e **Archivio Dossier & Registro Proattivo** integrato (35 report navigabili in tempo reale).

---

## ⚡ Fast & Intuitive Anki CLI (`core/anki_cli.py`)

```bash
# 1. Ispezione conteggi SRS live, code e versione schema (NVMe storage /opt/japan)
python3 core/anki_cli.py status

# 2. Sincronizzazione Protobuf con AnkiWeb in ~1-3s (pre-sync snapshot, pipeline, push)
python3 core/anki_cli.py sync

# 3. Verifica integrità SQLite, orfani e backup snapshot atomico
python3 core/anki_cli.py check

# 4. Spalmatura picchi di ripasso arretrati su N giorni (default: 14)
python3 core/anki_cli.py reschedule --days 14
```

---

## 🛡️ Invarianti di Sviluppo & Governance

1. **Limite Rigoroso $\le 200$ Righe per File**: Nessun file Python, JS o HTML può superare le 200 righe.
2. **Nessun Commit non Verificato**: Ogni mutazione viene validata con probe fisiche e registrata in [`.agents/feature-tests.json`](file:///mnt/workspaces/japan/.agents/feature-tests.json).
3. **Divieto di Modifiche tramite Script Python Estemporanei**: Rispetto della Regola 22 (solo tool deterministici `replace_file_content` o `write_to_file`).
4. **Anticipazione Proattiva Costante**: Consultazione e aggiornamento continuo di [`research/registro_proattivo_rischi_e_soluzioni_mext.md`](file:///mnt/workspaces/japan/research/registro_proattivo_rischi_e_soluzioni_mext.md).
