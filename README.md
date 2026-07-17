# NC Renamer

**GitHub:** [https://github.com/uzuran/NCRenamer](https://github.com/uzuran/NCRenamer)

A desktop utility that validates and corrects material codes embedded in CNC NC files,
manages a laser burn table, tracks work tasks, and stores leftover parts —
all from a single GUI with Czech/English support.

---

## About

NC Renamer was built for CNC laser cutting workshops that need a simple, reliable tool
to keep NC program files consistent and to log every burn operation without relying on
a heavy ERP or database system.

Everything runs from a single executable placed on a shared network drive.
No installation, no server, no configuration — just launch and work.

| | |
|---|---|
| **Author** | Černopaščenko Arťom |
| **Version** | 3.3.0 |
| **License** | CC BY-NC-ND 4.0 |
| **Repository** | [github.com/uzuran/NCRenamer](https://github.com/uzuran/NCRenamer) |
| **Language** | Python 3.12 + CustomTkinter |
| **Platform** | Windows (frozen) / Linux / macOS (from source) |

---

## Features

### NC File Renamer
- **Bulk processing** — select any number of `.NC` files and fix them in one click
- **Material mapping** — add, edit, or remove incorrect→correct code pairs through the built-in materials manager; stored as shared JSON visible to all users
- **Space-inference fallback** — automatically inserts the missing space between numeric code and suffix (e.g. `1.4301Brus` → `1.4301 Brus`) when no explicit mapping exists
- **Real-time progress bar** — file-by-file feedback during processing

### Burn Table
- **Steel and aluminium tabs** — each backed by its own Excel sheet inside one workbook per user
- **Batch NC loading** — select multiple `.NC` / `.SCH` files; records are sorted and written in one operation with a separator row
- **Duplicate detection with confirmation** — warns when a program already exists in the same sheet or the other sheet; lets the operator override and add it anyway
- **Print support** — print selected rows directly from the table view
- **Free-slot detection** — shows how many rows remain before the table is full

### Leftover Parts Storage
- **Add / edit / delete** leftover sheet parts with part number, storage location, and notes
- **Image attach** — paste any image from clipboard (Ctrl+V); saved as PNG, shown as thumbnail; click to open in system viewer
- **Search** by part number (live filter)
- **Shared across users** — JSON-backed, same real-time sync as todos

### Todo List
- **Add / edit / delete tasks** with a timestamp (date and time recorded on creation)
- **Mark done / pending** — done items shown in grey, sorted to the bottom
- **Double-click detail popup** — opens the full note text in a scrollable window
- **Shared across all users** — any user's additions or completions are visible to every other user in real time

### Multi-user / Real-time sync
- **Hybrid workspace** — shared data (materials, todos) in one place; per-user data (burn table, settings) isolated per Windows login name
- **File-watcher auto-refresh** — all TreeViews update automatically within ~500 ms when another user or app instance changes a shared file; no reload button required
- **Network deployment** — place the executable on a shared network drive; every machine that launches it shares the same `shared/` directory and gets its own `users/<name>/` folder automatically

### General
- **Bug report email** — one-click mailto with an auto-incremented subject line; counter is password-protected and persists between sessions
- **Light / Dark mode toggle** — stored in user settings
- **Czech / English UI** — switchable at runtime without restart
- **Auto-update check** — queries GitHub for a newer release on launch

---

## Project structure

```
NCRenamer/
├── app/
│   ├── models/                     # Domain logic and data (no UI imports)
│   │   ├── email_model.py              # Bug-report counter persistence
│   │   ├── formatter_model.py          # NC file validation and rewriting
│   │   ├── material_repository.py      # Material mapping JSON CRUD
│   │   ├── part_storage_repository.py  # Leftover parts JSON CRUD + image storage
│   │   ├── password_model.py           # Password verification
│   │   ├── settings_model.py           # JSON settings persistence
│   │   └── todo_repository.py          # Todo-item JSON CRUD
│   ├── viewmodels/                 # Mediators between models and views (no CTk imports)
│   │   ├── add_material_view_model.py
│   │   ├── main_view_model.py
│   │   ├── materials_view_model.py
│   │   ├── part_storage_view_model.py
│   │   ├── password_view_model.py
│   │   ├── settings_view_model.py
│   │   └── todo_view_model.py
│   ├── views/                      # customtkinter frames (UI only)
│   │   ├── main_frame.py
│   │   ├── materials_frame.py
│   │   ├── add_material_frame.py
│   │   ├── burn_table_frame.py
│   │   ├── part_storage_frame.py
│   │   ├── settings_frame.py
│   │   └── todo_frame.py
│   ├── burn_table/                 # Burn-table sub-application
│   │   ├── models/                     # BurnRecord, TableStatus
│   │   ├── services/                   # ExcelReader, ExcelWriter, XmlParser, …
│   │   ├── viewmodels/                 # BurnViewModel, PerformanceRecorder, PrintManager
│   │   ├── views/                      # BurnDashboard (standalone mode)
│   │   └── main.py                     # Factory: create_view_model()
│   ├── services/
│   │   └── update_checker.py           # GitHub version check
│   ├── translations/
│   │   └── translations.py             # Czech / English string dictionaries
│   └── utils/
│       ├── file_watcher.py             # Polling file-watcher for real-time sync
│       ├── resource_path.py            # PyInstaller-aware asset resolution
│       ├── shared_storage.py           # exe_dir() + file_lock() shared by repositories
│       └── workspace.py                # Hybrid shared/per-user path resolver
├── tests/
│   ├── unit/               # Pure unit tests, no filesystem or GUI
│   └── integration/        # Real filesystem, real repository
├── img/                    # UI icons
├── app.py                  # Entry point
├── Makefile
├── pyproject.toml          # Ruff, mypy, pytest configuration
├── .pre-commit-config.yaml
└── requirements.txt
```

---

## Architecture

### MVVM layers

The project follows **MVVM** (Model – View – ViewModel):

| Layer | Allowed to import | Must not import |
|---|---|---|
| Model | stdlib, third-party | views, viewmodels, customtkinter |
| ViewModel | models | views, customtkinter |
| View | viewmodels, customtkinter | models directly |

The burn table reuses the same pattern as the main app — `BurnViewModel` is assembled by a factory function (`create_view_model`) and injected into the view with no direct service access from the UI layer.

### Observer / auto-refresh

Every ViewModel exposes `subscribe(callback)` / `unsubscribe(callback)` / `_notify()`. Views register `reload_treeview` in their constructor. After any successful CRUD operation the ViewModel calls `_notify()`, which calls every registered callback on the main thread — so the TreeView updates immediately without the view needing to know what changed.

### Hybrid workspace

```
<exe-dir>/
  shared/
    materials.json   ← one file, shared by every user on the machine / network
    todo.json        ← same
  users/
    alice/
      settings.json  ← Alice's appearance, language
      burn_table.xlsx← Alice's burn log
    bob/
      settings.json
      burn_table.xlsx
```

The workspace root is always the directory that contains the executable.  
In a frozen build this is `Path(sys.executable).parent`; in development it is the project root.

### Real-time sync

A `FileWatcher` daemon thread polls file modification times every 500 ms.

```
External write to shared/materials.json
  → FileWatcher detects mtime change
  → root.after(0, _on_materials_changed)   ← marshalled to main thread
  → materials_frame.reload_treeview()
  → add_material_frame.reload_treeview()
```

The same pattern applies to `todo.json` and `users/<name>/burn_table.xlsx`.  
Callbacks always run on the tkinter main thread — no locking needed in the view layer.

#### Network deployment

Place `NCRenamer.exe` on a shared network drive. Every user who launches it from there automatically reads from the same `shared/` folder and writes to their own `users/<windows-login>/` sub-folder. Changes made by User A are visible on User B's screen within ~500 ms with no manual refresh.

---

## Requirements

- Python 3.12+
- Dependencies listed in `requirements.txt`

---

## Installation

```bash
git clone https://github.com/uzuran/NCRenamer.git
cd NCRenamer
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
make install-dev
pre-commit install
```

---

## Running

```bash
make run          # Main application
make run-burn     # Burn table (standalone)
```

Or directly:

```bash
python3 app.py
```

---

## How it works

Each NC file produced by the CAM system encodes the material on **line 4** in the format:

```
(MA/1.4301)
(MA/1.0037 S235JRG2)
```

NC Renamer applies three correction strategies in order:

1. **JSON lookup** — the material key is normalised (spaces removed, uppercased) and looked up in `shared/materials.json`. If a match is found the line is rewritten with the canonical value.
2. **Space inference** — if no mapping exists but the key contains a numeric code immediately followed by an alphabetic suffix (e.g. `1.4301Brus`), a space is inserted automatically.
3. **No-op** — if the line already matches the canonical pattern it is left unchanged.

The file is only written to disk when a change is actually made.

---

## Material mappings

Mappings are stored in `shared/materials.json` (created automatically on first launch):

```json
[
  ["1.4301BRUS-4.0", "1.4301 brus"],
  ["1.0037S235JRG2", "1.0037 S235JRG2"]
]
```

The built-in **Materials** screen lets you add, edit, or remove entries without touching the file directly. Changes are immediately visible to all running instances via the file watcher.

---

## Development

### Make targets

```
make run                 Launch the application
make run-burn            Launch the burn table (standalone)
make test                Full test suite
make test-unit           Unit tests only
make test-integration    Integration tests only
make coverage            Tests + terminal coverage report
make coverage-html       Tests + open HTML coverage report
make lint                Ruff lint check
make format              Ruff format check
make typecheck           mypy type check
make check               All pre-commit hooks
make install             Install runtime dependencies
make install-dev         Install runtime + dev dependencies
make clean               Remove caches and build artefacts
```

### Running tests

```bash
make test
# or
python3 -m pytest tests/
```

832 tests — unit and integration — covering models, viewmodels, the NC processing pipeline, burn table validation (including cross-sheet duplicate detection), todo repository, shared storage, workspace path resolution, file-watcher detection, and multi-user sync.

### Code quality

All three tools run automatically on every commit via pre-commit:

```bash
make check   # ruff lint + ruff format + mypy + trailing-whitespace + ...
```

To run only mypy or ruff:

```bash
make typecheck
make lint
```

---

## Building a Windows executable

```bash
make build
```

Uses PyInstaller via `NCRenamer.spec`. The resulting binary is written to `dist/`.  
On first launch the workspace directories (`shared/`, `users/<name>/`) are created automatically next to the executable.

---

## Version

`3.3.0` — see [app/version.py](app/version.py)

---

## License

Copyright (c) 2026 Arťom Černopaščenko

NC/SCH Renamer is licensed under the
[Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International License](https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode).

You may share this software in its original form for non-commercial purposes only.
Modification, adaptation, and commercial use are not permitted.
See [LICENSE.txt](LICENSE.txt) for the full summary.
