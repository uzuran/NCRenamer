@echo off
setlocal EnableDelayedExpansion
chcp 65001 > nul

echo.
echo  ============================================================
echo   NCRenamer v0.2.0  --  Windows Build
echo  ============================================================
echo.

:: ── check Python ─────────────────────────────────────────────────────────────
python --version > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo  [ERROR] Python not found. Install Python 3.12+ and add it to PATH.
    pause & exit /b 1
)

:: ── install / upgrade build tools ────────────────────────────────────────────
echo  [1/4] Installing dependencies...
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
pip install --quiet pyinstaller
if %ERRORLEVEL% neq 0 (
    echo  [ERROR] pip install failed.
    pause & exit /b 1
)

:: ── clean previous build ─────────────────────────────────────────────────────
echo  [2/4] Cleaning previous build...
if exist build   rmdir /s /q build
if exist dist    rmdir /s /q dist

:: ── build ────────────────────────────────────────────────────────────────────
echo  [3/4] Building NCRenamer.exe ...
pyinstaller NCRenamer.spec --clean --noconfirm
if %ERRORLEVEL% neq 0 (
    echo.
    echo  [ERROR] PyInstaller failed. Check the output above for details.
    pause & exit /b 1
)

:: ── copy table file next to exe ───────────────────────────────────────────────
echo  [4/5] Copying CNCs\laser.xls next to exe...
if not exist dist\CNCs mkdir dist\CNCs
if exist CNCs\laser.xls (
    copy /y CNCs\laser.xls dist\CNCs\laser.xls > nul
    echo         Copied: CNCs\laser.xls
) else (
    echo         WARNING: CNCs\laser.xls not found - copy it manually next to the exe.
)

:: ── done ─────────────────────────────────────────────────────────────────────
echo  [5/5] Done.
echo.
echo  Output:  dist\NCRenamer.exe
echo  Table:   dist\CNCs\laser.xls
echo.
echo  ============================================================
echo   Build successful!
echo  ============================================================
echo.
pause
