# NC Renamer

A desktop utility that validates and corrects material codes embedded in CNC NC files,
manages a laser burn table, and tracks work tasks — all from a single GUI with Czech/English support.

---

## Features

### NC File Renamer
- **Bulk processing** — select any number of `.NC` files and fix them in one click
- **CSV-driven material mapping** — add, edit, or remove incorrect→correct code pairs through the built-in materials manager
- **Space-inference fallback** — automatically inserts the missing space between numeric code and suffix (e.g. `1.4301Brus` → `1.4301 Brus`) when no explicit mapping exists
- **Real-time progress bar** — file-by-file feedback during processing

### Burn Table
- **Steel and aluminium tabs** — each backed by its own Excel sheet, loaded from the same file
- **Batch NC loading** — drag and drop or select multiple `.NC` / `.SCH` files; records are sorted and written in one operation with a separator row
- **Duplicate detection** — rejects programs already in the **same** sheet or the **other** sheet (cross-sheet validation, case-insensitive)
- **Print support** — print selected rows directly from the table view
- **Free-slot detection** — shows how many rows remain before the table is full

### Todo List
- **Add / edit / delete tasks** with a timestamp (date and time recorded on creation)
- **Mark done / pending** — done items shown in grey, sorted to the bottom
- **Double-click detail popup** — opens the full note text in a scrollable window

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
│   │   ├── material_repository.py      # Tab-separated CSV CRUD
│   │   ├── password_model.py           # Password verification
│   │   ├── settings_model.py           # JSON settings persistence
│   │   └── todo_repository.py          # Todo-item JSON CRUD
│   ├── viewmodels/                 # Mediators between models and views (no CTk imports)
│   │   ├── main_view_model.py
│   │   ├── materials_view_model.py
│   │   ├── password_view_model.py
│   │   ├── settings_view_model.py
│   │   └── todo_view_model.py
│   ├── views/                      # customtkinter frames (UI only)
│   │   ├── main_frame.py
│   │   ├── materials_frame.py
│   │   ├── add_material_frame.py
│   │   ├── burn_table_frame.py
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
│       ├── resource_path.py            # PyInstaller-aware asset resolution
│       └── shared_storage.py           # exe_dir() + file_lock() shared by repositories
├── CNCs/
│   └── laser.xls           # Burn table Excel file (steel sheet 0, aluminium sheet 1)
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

The project follows **MVVM** (Model – View – ViewModel):

| Layer | Allowed to import | Must not import |
|---|---|---|
| Model | stdlib, third-party | views, viewmodels, customtkinter |
| ViewModel | models | views, customtkinter |
| View | viewmodels, customtkinter | models directly |

The burn table reuses the same pattern as the main app — `BurnViewModel` is assembled by a factory function (`create_view_model`) and injected into the view with no direct service access from the UI layer.

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

1. **CSV lookup** — the material key is normalised (spaces removed, uppercased) and looked up in `materials_new.csv`. If a match is found the line is rewritten with the canonical value.
2. **Space inference** — if no CSV match exists but the key contains a numeric code immediately followed by an alphabetic suffix (e.g. `1.4301Brus`), a space is inserted automatically.
3. **No-op** — if the line already matches the canonical pattern `(MA/\d\.\d{4}...)` it is left unchanged.

The file is only written to disk when a change is actually made.

---

## Material mapping CSV

The mapping lives at `CNCs/materials_new.csv` (tab-separated, no header):

```
incorrect_code<TAB>correct_code
1.4301BRUS-4.0	1.4301 brus
1.0037S235JRG2	1.0037 S235JRG2
```

On first launch the seed CSV is copied to the user's AppData directory so changes are not lost across updates. The built-in **Materials** screen lets you add or remove entries without editing the file directly.

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

521 tests — unit and integration — covering models, viewmodels, the NC processing pipeline, burn table validation (including cross-sheet duplicate detection), todo repository, and shared storage.

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

Uses PyInstaller via `NCRenamer.spec`. The resulting binary is written to `dist/`. The `laser.xls` burn table is placed next to the executable (not bundled inside it) so users can edit it freely.

---

## Version

`2.3.0` — see [app/version.py](app/version.py)

Author: Černopaščenko Arťom

---

## License

Copyright (c) 2026 Arťom Černopaščenko

NC/SCH Renamer is licensed under the
[Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International License](https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode).

You may share this software in its original form for non-commercial purposes only.
Modification, adaptation, and commercial use are not permitted.
See [LICENSE.txt](LICENSE.txt) for the full summary.
