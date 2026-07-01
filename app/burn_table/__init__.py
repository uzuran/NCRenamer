"""app.burn_table — production burn-record tracking module.

Strict MVVM layout:
    models/      — pure dataclasses (no imports from this package)
    services/    — file I/O adapters (import models only)
    viewmodels/  — state + operations (import models + services)
    views/       — Tkinter widgets (import viewmodels only)

Entry point: ``python -m app.burn_table``
"""
