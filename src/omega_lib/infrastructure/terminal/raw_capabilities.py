# Copyright (c) 2026 kraynux - Licence MIT
"""Lecture des signaux bruts du terminal (variables d'environnement, taille).
Porte depuis omega-scan/omega-stress dans omega-lib (D-008), y compris les
marqueurs Terminator/Konsole/GNOME Terminal (TERM/TERM_PROGRAM ne suffisent
pas a les identifier)."""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RawTerminalSignals:
    """Signaux tels que remontes par le systeme, sans aucune interpretation."""

    term: str
    term_program: str
    colorterm: str
    is_ssh: bool
    columns: int
    rows: int
    has_terminator_marker: bool
    has_konsole_marker: bool
    has_gnome_terminal_marker: bool


def read_raw_signals() -> RawTerminalSignals:
    """Lit les variables d'environnement et la taille de terminal actuelles.
    Ne decide de rien : voir fallback_resolver.py pour l'interpretation."""
    columns, rows = shutil.get_terminal_size(fallback=(80, 24))
    return RawTerminalSignals(
        term=os.environ.get("TERM", ""),
        term_program=os.environ.get("TERM_PROGRAM", ""),
        colorterm=os.environ.get("COLORTERM", ""),
        is_ssh="SSH_CLIENT" in os.environ or "SSH_CONNECTION" in os.environ,
        columns=columns,
        rows=rows,
        has_terminator_marker="TERMINATOR_UUID" in os.environ,
        has_konsole_marker="KONSOLE_VERSION" in os.environ,
        has_gnome_terminal_marker=(
            "GNOME_TERMINAL_SCREEN" in os.environ or "GNOME_TERMINAL_SERVICE" in os.environ
        ),
    )
