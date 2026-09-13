# Copyright (c) 2026 kraynux - Licence MIT
"""Resolution du nom de famille de terminal a partir des signaux bruts.
Porte depuis omega-scan/omega-stress dans omega-lib (D-008). Les noms
retournes doivent rester synchronises avec les cles de terminal/policies.py
— une famille non reconnue s'y degrade silencieusement vers le profil de
rendu par defaut, jamais une erreur ici."""
from __future__ import annotations

from omega_lib.infrastructure.terminal.raw_capabilities import RawTerminalSignals

_KNOWN_FAMILIES: tuple[str, ...] = (
    "ghostty",
    "alacritty",
    "wezterm",
    "kitty",
    "konsole",
    "terminator",
    "xfce4-terminal",
)


def resolve_family(signals: RawTerminalSignals) -> str:
    """Traduit des signaux bruts en un nom de famille normalise."""
    term = signals.term.lower()
    term_program = signals.term_program.lower()

    if signals.is_ssh:
        modern = signals.colorterm.lower() in ("truecolor", "24bit") or "256" in term
        return "ssh-modern" if modern else "ssh-legacy"

    if signals.has_terminator_marker:
        return "terminator"
    if signals.has_konsole_marker:
        return "konsole"
    if signals.has_gnome_terminal_marker:
        return "gnome-terminal"

    for family in _KNOWN_FAMILIES:
        if family in term or family in term_program:
            return family

    if "gnome" in term or "gnome" in term_program:
        return "gnome-terminal"
    if "rxvt" in term:
        return "urxvt"
    if term == "linux":
        return "linux-tty"
    if "xterm" in term:
        return "xterm"

    return term or "unknown"
