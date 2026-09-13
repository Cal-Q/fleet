# 🛡️ Dossier Strategico: Prevenzione Rischi & Criticità Latenti — Borsa MEXT FY2027

**Data di Emissione**: 14 Settembre 2026  
**Candidato**: Patrik Potenza (UniTO L-11, Matricola 993141)  
**Obiettivo Primario**: Borsa di Studio MEXT Japanese Studies (*Nikken-sei*) — Ambasciata del Giappone a Roma  
**Data Esame Prevista**: ~20 Febbraio 2027 (~159 giorni all'esame)  

---

## 1. Premessa di Partnership Cognitiva

Un percorso di preparazione competitiva per una borsa di studio a posti limitati (2-4 vincitori su scala nazionale italiana) non può essere reattivo. Aspettare che una criticità emerga durante lo studio significa affrontarla quando il costo temporale ed emotivo per risolverla è moltiplicato per dieci.

Il compito di questo sistema è **mappare l'orizzonte, prevedere i colli di bottiglia invisibili e disinnescarli prima che si manifestino**.

Il presente dossier identifica i **5 macro-rischi latenti** che si presenteranno tra ottobre 2026 e febbraio 2027 e stabilisce le relative contromisure ingegnerizzate.

---

## 2. Mappa delle 5 Criticità Latenti

```
[Settembre] ───────> [Ottobre - Novembre] ─────────> [Dicembre - Gennaio] ───────> [Febbraio 2027]
   │                         │                              │                            │
   ▼                         ▼                              ▼                            ▼
RISCHIO 2                 RISCHIO 4                      RISCHIO 5                    RISCHIO 1 & 3
Familiarità Fittizia      Valanga SRS &                 Strozzature Burocratiche     Muro dei 60 Minuti &
& Distrattori             Semestre UniTO                UniTO / Medico MEXT          Imboscata Colloquio
```

---

### CRITICITÀ 1: Il "Muro dei 60 Minuti" e il Collasso del Pacing all'Ambasciata

* **Natura del Rischio**:  
  A differenza del JLPT (in cui le sezioni di vocabolario, grammatica e lettura sono separate con tempi generosi), l'esame scritto MEXT comprime **100 quesiti in un unico foglio da 60 minuti** (Part A: 35 pt, Part B: 35 pt, Part C: 30 pt compresi due brani di lettura accademica).  
  Il tempo medio disponibile è di appena **36 secondi a domanda**.
* **La Trappola Futura**:  
  Se ci si allena senza un cronometro rigido a domanda, l'istinto porta a riflettere per 60-90 secondi su un kanji o una particella di Parte A. In aula d'esame a Roma, lo studente giunge al 50° minuto mentre è ancora a metà di Parte B, lasciando in bianco l'intera Parte C e venendo matematicamente eliminato.
* **Contromisura Preventiva Implementata**:
  1. **Pacing Target Fisso per Parte A**: Target calibrato a **$\le 25$ secondi a quesito** (la Parte A deve essere chiusa in massimo 15 minuti netti).
  2. **Pacing Target per Parte B**: Target calibrato a **$\le 40$ secondi a quesito** (massimo 20 minuti netti).
  3. **Finestra di Sicurezza per Parte C**: Riservare almeno 22-25 minuti per la lettura veloce e l'eliminazione dei distrattori sui testi lunghi.
  4. **Metrica Attiva sul Portale**: La dashboard `japan.calq.it` traccia i `seconds_per_question` di ogni sessione e segnala con allerta visiva qualsiasi ritmo superiore a 35s.

---

### CRITICITÀ 2: L'Illusione dell'Anki Passivo & i Distrattori Fonetico-Grafici

* **Natura del Rischio**:  
  Nei mazzi Anki e nell'apprendimento digitale, il riconoscimento è prevalentemente *passivo*: si vede il fronte della carta e il cervello riconosce la sagoma complessiva del kanji o della parola.  
  Nel test MEXT, i quesiti di Parte A non chiedono una traduzione libera, ma pongono **4 distrattori ingegnerizzati sui punti deboli fonetici e grafici dei non-madrelingua**.
* **La Trappola Futura**:
  - **Trappola Fonetica**: Vocali lunghe (*Chōon*) vs brevi (`しょうがくせい` vs `しょがくせい`, `つうやく` vs `つやく`), geminate (*Sokuon*) (`けっか` vs `けつか`), sonore/sorde (*Dakuon*) (`しんぶん` vs `じんぶん`). Chi conosce la parola "a spanne" cade nel distrattore nel 50% dei casi.
  - **Trappola Grafica**: Kanji con radicali quasi identici (`待` aspettare vs `持` tenere; `買` comprare vs `貸` prestare; `体` corpo vs `休` riposare).
* **Contromisura Preventiva Implementata**:
  1. **Banca Dati Inedita Dedicata (`drill_pool_part_a.json`)**: Creazione di quesiti originali che riproducono esattamente questi 4 pattern di distrattore, con rotazione giornaliera automatica (zero sovrapposizione con i mock ufficiali 2017-2019 e zero frasi riciclate da Bunpro).
  2. **Spiegazione Diagnostica dei Distrattori**: Il feedback post-risposta non dice solo "A è giusta", ma chiarisce l'inganno fonetico o il radicale ingannevole delle opzioni B, C e D.

---

### CRITICITÀ 3: L'Imboscata del Colloquio Orale nello Stesso Pomeriggio

* **Natura del Rischio**:  
  A Roma la selezione è a sbarramento immediato:
  - Ore 10:00: Test Scritto (60 min).
  - Ore 13:30: Affissione graduatoria ammessi al colloquio (soglia ~58-65%).
  - Ore 14:30: Inizio colloqui orali individuali con la commissione diplomatica e accademica.
* **La Trappola Futura**:  
  Passare da 60 minuti di lettura muta a sostenere una conversazione formale in Keigo di fronte a 3 diplomatici giapponesi provoca il cosiddetto "blocco neuromuscolare" se non si è praticata la produzione vocale attiva. Inoltre, la domanda killer è sempre:  
  *「なぜトリノ大学ではなく、日本でなければならないのですか。」* (*Perché deve andare in Giappone e non può svolgere la ricerca a Torino?*).  
  Rispondere con entusiasmo generico ("perché amo il Giappone") è eliminatorio.
* **Contromisura Preventiva Implementata**:
  1. **Micro-Drill di Shadowing Orale (5 min/die)**: A partire da Ottobre, inserimento di una domanda fissa d'ambasciata alla settimana con risposta vocale ad alta voce.
  2. **Blindatura dello Study Plan "Terzi Luoghi & Sinoira Gang"**: La risposta è già strutturata: osservazione etnografica diretta sul campo nelle card room e palestre Pokémon di Tokyo/Kyoto, accesso agli archivi cartacei di sociologia giovanile introvabili in Italia, e ponte diretto per la tesi di laurea L-11 a UniTO al rientro.

---

### CRITICITÀ 4: La "Valanga SRS" & la Saturazione da Inizio Semestre UniTO

* **Natura del Rischio**:  
  A inizio ottobre riprendono le lezioni del 2° anno a Palazzo Nuovo (UniTO). Se gli algoritmi di ripetizione spaziata (SRS Anki) accumulano carte senza un tetto matematico, il carico giornaliero può schizzare a 150-200 card/die contemporaneamente alle lezioni universitarie.
* **La Trappola Futura**:  
  Un accumulo di 3 giorni di arretrati crea una coda insormontabile di 400 card, innescando frustrazione, senso di colpa e abbandono della routine.
* **Contromisura Preventiva Implementata**:
  1. **Tetto Massimo Giornaliero di Revisione**: Anki calibrato con ritenzione mirata al 90% (FSRS) e tempo massimo non superiore a **35-40 minuti** per lo Slot 1.
  2. **Invariante dei Buffer Days (Giorni Cuscinetto)**: 1 giorno ogni 7 (23 giorni cuscinetto complessivi nel piano a 161 giorni) privo di nuovo materiale, dedicato esclusivamente ad assorbire imprevisti accademici o ripasso leggero.

---

### CRITICITÀ 5: Le Strozzature Burocratiche UniTO & Certificazioni Mediche

* **Natura del Rischio**:  
  Il bando ufficiale dell'Ambasciata esce tipicamente tra metà dicembre e inizio gennaio, con scadenza tassativa nei primi giorni di febbraio. Molti candidati sottovalutano i tempi della burocrazia italiana.
* **La Trappola Futura**:
  - **Certificato Segreteria UniTO**: L'autocertificazione online di MyUniTO **non è valida**. Serve il certificato ufficiale con esami su carta resa legale, timbro a inchiostro e firma originale del funzionario (Polo Scienze Umanistiche / Palazzo Nuovo). A dicembre/gennaio, tra festività e sessione d'esami, i tempi di rilascio possono raggiungere le 3-4 settimane.
  - **Lettera di Raccomandazione**: Chiederla a un docente UniTO a metà gennaio significa trovarlo sommerso da appelli d'esame.
  - **Certificate of Health Ufficiale MEXT**: Richiede esami ematici, urine e una **lastra al torace (Rx Torace)** con referto medico firmato.
* **Contromisura Preventiva Implementata (Timeline Burocratica Deterministica)**:
  - **15 Novembre 2026**: Primo contatto con il docente di riferimento a UniTO per preavvisare la richiesta della lettera di raccomandazione, fornendogli già bozza di Study Plan e CV.
  - **01 Dicembre 2026**: Richiesta formale alla Segreteria Studenti di Palazzo Nuovo del certificato di iscrizione con esami per uso borsa estera.
  - **15 Dicembre 2026**: Prenotazione della visita medica e dell'Rx Torace per la prima settimana di gennaio 2027.
  - **15 Gennaio 2027**: Tutti i documenti cartacei digitalizzati e archiviati in `/opt/japan/applications/`.

---

## 3. Matrice Riassuntiva delle Azioni Preventive

| Area di Rischio | Momento Critico | Azione Preventiva Programmata | Strumento / File di Riferimento |
| :--- | :---: | :--- | :--- |
| **Pacing 60 min** | Novembre – Febbraio | Soglia $\le 30$s su Parte A; allerta ritmo su `japan.calq.it` | `academic/exam_analytics.py` & UI Timer |
| **Distrattori Parte A** | Quotidiano (Slot 4) | Pool inedito 100+ quesiti con rotazione e blindatura 2017-2019 | `exams/drill_pool_part_a.json` |
| **Colloquio Orale** | Dicembre – Febbraio | Risposte codificate su Studio dei Terzi Luoghi e legame tesi UniTO | `japanese/interview_mastery.md` |
| **Carico Anki** | Ottobre – Novembre | Limite 40 min/die, parametrizzazione FSRS e buffer days | `research/dossier_161_day_master_plan.md` |
| **Burocrazia UniTO** | 15 Nov – 15 Gen | Protocollo anticipato (Segreteria, Lettera Docente, Rx Torace) | `applications/OVERVIEW_UNITO.md` |
