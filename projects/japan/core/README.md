# Core Anki SRS Engine & Sync Subsystem

This directory houses the Anki synchronization, pipeline execution, and collection manipulation modules.

---

## 📁 Key Components

| File | Purpose |
| :--- | :--- |
| [`anki_cli.py`](file:///mnt/workspaces/japan/core/anki_cli.py) | **Primary user/agent CLI**: `status`, `sync`, `reschedule`. Fast high-contrast terminal interface. |
| [`sync_and_push.py`](file:///mnt/workspaces/japan/core/sync_and_push.py) | **Full pipeline orchestrator**: Pre-sync pull $\to$ deck regeneration $\to$ post-sync push. Includes transparent auto-delegation to IONOS when executed on Oracle VPS. |
| [`sync_worker.py`](file:///mnt/workspaces/japan/core/sync_worker.py) | Single-writer threading lock (`_LOCK`) and async runner used by FastAPI web routes (`/api/bunki/sync`, `/api/bunki/verify_srs`). |
| [`sync_quick.py`](file:///mnt/workspaces/japan/core/sync_quick.py) | Lightweight merger for pending Bunpro sentences and vocabulary without a full multi-deck rebuild. |
| [`anki_sync/pipeline.py`](file:///mnt/workspaces/japan/core/anki_sync/pipeline.py) | Computes deck cards and triggers direct SQLite batch writes with strict `allow_add=False` and `allow_delete=False` guards on protected decks. |
| [`anki_sync/anki_direct_writer.py`](file:///mnt/workspaces/japan/core/anki_sync/anki_direct_writer.py) | High-performance direct SQLite updates directly on `collection.anki2` (Schema 18). |
| [`anki_sync/sync_helpers.py`](file:///mnt/workspaces/japan/core/anki_sync/sync_helpers.py) | Host detection (`is_primary_anki_host`), remote dispatching, and process lock queries. |

---

## 🚀 Quick Recipes

### 1. View Live SRS Queue
```bash
python3 core/anki_cli.py status
```

### 2. Manual Immediate Sync
```bash
python3 core/anki_cli.py sync
```

### 3. Smooth Out Overdue Card Spike
```bash
python3 core/anki_cli.py reschedule --days 14
```

---

## 🔒 Safety & Invariant Guarantees
- **No GUI Dependency**: All syncing is done headlessly using native Anki 26.08 Protobuf endpoints.
- **Single-Writer Integrity**: `sync_worker.py` enforces a mutual-exclusion lock (`_LOCK`) preventing concurrent SQLite writes.
- **Deck Protection**: Travel Vocab and Travel Kanji decks reject accidental new card insertions (`allow_add=False`).
