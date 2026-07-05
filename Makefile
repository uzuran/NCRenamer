PYTHON := python3
PIP    := pip3

.PHONY: help run run-burn test test-unit test-integration test-verbose \
        coverage coverage-html lint format typecheck check \
        install install-dev build clean

# ─── Default ────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "  Run"
	@echo "    run                 Launch the NCRenamer application"
	@echo "    run-burn            Launch the burn-table application"
	@echo ""
	@echo "  Tests"
	@echo "    test                Run full test suite"
	@echo "    test-unit           Run unit tests only"
	@echo "    test-integration    Run integration tests only"
	@echo "    test-verbose        Run full suite with verbose output"
	@echo "    coverage            Run tests with terminal coverage report"
	@echo "    coverage-html       Run tests and open HTML coverage report"
	@echo ""
	@echo "  Code quality"
	@echo "    lint                Ruff lint check (no auto-fix)"
	@echo "    format              Ruff format check (no auto-fix)"
	@echo "    typecheck           Mypy type check"
	@echo "    check               Run all pre-commit hooks (lint + format + mypy)"
	@echo ""
	@echo "  Dependencies"
	@echo "    install             Install runtime dependencies"
	@echo "    install-dev         Install runtime + dev dependencies"
	@echo ""
	@echo "  Build"
	@echo "    build               Compile Windows .exe with PyInstaller"
	@echo ""
	@echo "  Housekeeping"
	@echo "    clean               Remove build artefacts and caches"
	@echo ""

# ─── Run ────────────────────────────────────────────────────────────────────

run:
	$(PYTHON) app.py

run-burn:
	$(PYTHON) -m app.burn_table

# ─── Tests ──────────────────────────────────────────────────────────────────

test:
	$(PYTHON) -m pytest tests/

test-unit:
	$(PYTHON) -m pytest tests/unit/

test-integration:
	$(PYTHON) -m pytest tests/integration/

test-verbose:
	$(PYTHON) -m pytest tests/ -v

coverage:
	$(PYTHON) -m pytest tests/ --cov=app --cov-report=term-missing

coverage-html:
	$(PYTHON) -m pytest tests/ --cov=app --cov-report=html
	@echo "Opening coverage report..."
	@xdg-open htmlcov/index.html 2>/dev/null || start htmlcov/index.html 2>/dev/null || echo "Open htmlcov/index.html manually."

# ─── Code quality ───────────────────────────────────────────────────────────

lint:
	$(PYTHON) -m ruff check app/ tests/

format:
	$(PYTHON) -m ruff format --check app/ tests/

typecheck:
	$(PYTHON) -m mypy app/ tests/

check:
	pre-commit run --all-files

# ─── Build ───────────────────────────────────────────────────────────────────
# Uses Windows Python via powershell.exe so the output is a .exe, not a Linux
# binary.  Works from both WSL and a Windows terminal (PowerShell / CMD).
# laser.xls is not bundled inside the exe — it lives next to it so users can
# edit it freely.

build:
	powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "python -m PyInstaller NCRenamer.spec --clean --noconfirm"
	powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "New-Item -Force -ItemType Directory 'dist\CNCs' | Out-Null; Copy-Item 'CNCs\laser.xls' 'dist\CNCs\laser.xls' -Force"

# ─── Dependencies ───────────────────────────────────────────────────────────

install:
	$(PIP) install -r requirements.txt

install-dev:
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-cov mypy ruff pre-commit hypothesis types-requests

# ─── Housekeeping ───────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	find . -type d -name htmlcov -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name ".coverage" -delete
	find . -name "coverage.xml" -delete
	rm -rf dist/ build/
