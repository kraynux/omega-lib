# Copyright (c) 2026 kraynux - Licence MIT
"""Implementation concrete du port TerminalDetector.
Porte depuis omega-scan/omega-stress dans omega-lib (D-008)."""
from __future__ import annotations

from omega_lib.infrastructure.terminal.fallback_resolver import resolve_family
from omega_lib.infrastructure.terminal.raw_capabilities import read_raw_signals
from omega_lib.terminal.models import TerminalSignals


class SystemTerminalDetector:
    """Implemente ports/terminal_detector.py::TerminalDetector. Nommee
    SystemTerminalDetector (pas TerminalDetector) pour ne pas porter le
    meme nom que le Protocol qu'elle implemente."""

    def detect(self) -> TerminalSignals:
        raw = read_raw_signals()
        return TerminalSignals(
            family=resolve_family(raw),
            columns=raw.columns,
            rows=raw.rows,
            is_ssh=raw.is_ssh,
        )
