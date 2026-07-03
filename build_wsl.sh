#!/usr/bin/env bash
# NCRenamer v0.2.0 — build Windows .exe from WSL
# Requires: Windows Python 3.12+ installed and on the Windows PATH

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WIN_PROJECT="$(wslpath -w "$SCRIPT_DIR")"
WIN_SCRIPT="${WIN_PROJECT}\\build.ps1"

echo ""
echo "  NCRenamer — building from WSL"
echo "  Windows project path: $WIN_PROJECT"
echo ""

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$WIN_SCRIPT"
