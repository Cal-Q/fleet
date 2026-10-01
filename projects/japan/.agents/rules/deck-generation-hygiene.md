# Deck Generation Hygiene & Anti-Archaic Invariant

## Overview
When generating Anki decks from dictionary databases (such as JMdict or KANJIDIC):
- Never delete downstream cards manually if they are produced by a generator: fix the generator logic upstream.
- Always filter out archaic, obsolete, rare, and irregular forms before adding words or kanji to study decks.

## Strict Invariants

1. **Zero Manual Card Deletions for Regenerable Sets**:
   - Deleting cards directly in Anki SQLite without fixing the generator is strictly forbidden.
   - Any manual delete will be undone on the next pipeline sync (`pipeline.py`).
   - Fix the source query or filtering logic in the deck generator, then let `sync_decks_batch(..., allow_delete=True)` naturally synchronize and purge cards.

2. **JMdict Semantic & Orthographic Filtering**:
   - **Semantic Level (`senses.misc`)**: Exclude any entry where all senses contain:
     - `archaic`
     - `obsolete term`
     - `rare term`
     - `historical term`
     - `outdated term`
   - **Orthographic Level (`reading_elements.info`)**: Exclude individual reading elements containing:
     - `word containing irregular kanji usage`
     - `word containing out-dated kanji or kanji usage`
     - `rarely used kanji form`
     - `search-only kanji form`
     - `irregular okurigana usage`
   - **Priority Resolution (`reading_elements.priority`)**:
     - When an entry lists multiple kanji spellings, give absolute priority to spellings with non-empty priority tags (`priority != []`).
     - Discard unprioritized alternative variants unless explicitly studied by the user.

3. **No Automatic Entry Activation from Single Kanji**:
   - Single kanji in `kanji_catalog` must NOT mark multi-kanji compound entries as `in_anki = 1` in `entries`.

4. **Root-Cause Deck Generator Parity (Strict Anti-Bandaid Invariant)**:
   - Ogni modifica al comportamento, layout, campo o contenuto delle carte in Bunki e Anki (es. letture multiple On/Kun, disambiguazione frasi, formattazione note) DEVE essere tassativamente risolta alla radice nel codice di rigenerazione dei mazzi (`core/anki_sync/pipeline.py`, `core/anki_sync/pipeline_helpers.py`, `sync_and_push.py`).
   - È severamente vietato applicare "bandaid" superficiali (wrapper lato client, patch a caldo nei soli endpoint API o renderer web) che lasciano il generatore a monte con la vecchia logica difettosa.
   - Il generatore deve produrre nativamente la struttura completa e canonica, in modo che ogni successiva rigenerazione (`sync_decks_batch`) propaghi in modo naturale e deterministico i dati corretti su tutti i client (AnkiWeb, AnkiDroid, Bunki Web, Standalone APK).
