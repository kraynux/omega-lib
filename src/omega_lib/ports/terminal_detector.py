# Copyright (c) 2026 kraynux - Licence MIT
"""Contrat de detection des signaux bruts du terminal.
Porte depuis omega-scan/omega-stress dans omega-lib (D-008)."""
from __future__ import annotations

from typing import Protocol

from omega_lib.terminal.models import TerminalSignals


class TerminalDetector(Protocol):
    """Implemente par omega_lib.infrastructure.terminal.detector."""

    def detect(self) -> TerminalSignals: ...
