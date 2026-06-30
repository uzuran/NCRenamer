# NC Renamer

A desktop utility that validates and corrects material codes embedded in CNC NC files.
NC Renamer reads line 4 of each file (the `(MA/...)` field), looks up the code against
a configurable CSV mapping table, and rewrites it in the canonical format — in bulk,
with a progress bar, and without leaving the GUI.

---

## Features

- **Bulk processing** — select any number of `.NC` files and fix them in one click
- **CSV-driven material mapping** — add, edit, or remove incorrect→correct code pairs through the built-in materials manager
- **Space-inference fallback** — automatically inserts the missing space between numeric code and suffix (e.g. `1.4301Brus` → `1.4301 Brus`) when no explicit mapping exists
- **Real-time progress bar** — file-by-file feedback during processing
- **Bug report email** — one-click mailto with an auto-incremented subject line; counter is password-protected and persists between sessions
- **Light / Dark mode toggle** — stored in user settings
- **Czech / English UI** — switchable at runtime without restart
- **Auto-update check** — on launch, queries GitHub for a newer version

---

## Project structure

```
NCRenamer/
├── app/
│   ├── models/             # Domain logic and data (no UI imports)
│   │   ├── email_model.py          # Bug-report counter persistence
│   │   ├── formatter_model.py      # NC file validation and rewriting
│   │   ├── material_repository.py  # Tab-separated CSV CRUD
│   │   ├── password_model.py       # Password verification
│   │   └── settings_model.py       # JSON settings persistence
│   ├── viewmodels/         # Mediators between models and views (no CTk imports)
│   │   ├── main_view_model.py
│   │   ├── materials_view_model.py
│   │   ├── password_view_model.py
│   │   └── settings_view_model.py
│   ├── views/              # customtkinter frames (UI only)
│   │   ├── main_frame.py
│   │   ├── materials_frame.py
│   │   ├── add_material_frame.py
│   │   └── settings_frame.py
│   ├── services/
│   │   └── update_checker.py       # GitHub version check
│   ├── translations/
│   │   └── translations.py         # Czech / English string dictionaries
│   └── utils/
│       └── resource_path.py        # PyInstaller-aware asset resolution
├── CNCs/
│   └── materials_new.csv   # Seed mapping table (incorrect_code → correct_code)
├── tests/
│   ├── unit/               # Pure unit tests, no filesystem or GUI
│   └── integration/        # Real filesystem, real repository
├── resources/              # Runtime JSON (settings, email counter)
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
make run
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

153 tests — unit and integration — covering models, viewmodels, and the NC processing pipeline.

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
pyinstaller app.spec
```

The resulting binary is written to `dist/`. The `.spec` file configures asset bundling (icons, CSV, translations).

---

## Version

`0.1.0` — see [app/version.py](app/version.py)

Author: Černopaščenko Arťom
