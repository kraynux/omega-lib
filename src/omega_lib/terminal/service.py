# Copyright (c) 2026 kraynux - Licence MIT
"""Decision du profil de rendu a partir des signaux bruts du terminal.
Porte depuis omega-scan/omega-stress dans omega-lib (D-008)."""
from __future__ import annotations

from omega_lib.terminal.models import TerminalProfile, TerminalSignals
from omega_lib.terminal.policies import (
    DEFAULT_RENDER_PROFILE,
    TERMINAL_FAMILY_PROFILES,
    most_restrictive,
    render_profile_ceiling_for_size,
)


def resolve_render_profile(signals: TerminalSignals) -> TerminalProfile:
    """Combine la famille de terminal et sa taille : le profil retenu est
    le plus restrictif des deux (une taille insuffisante degrade meme un
    terminal par ailleurs complet, jamais l'inverse)."""
    family_profile = TERMINAL_FAMILY_PROFILES.get(signals.family, DEFAULT_RENDER_PROFILE)
    size_ceiling = render_profile_ceiling_for_size(signals.columns, signals.rows)
    resolved = most_restrictive(family_profile, size_ceiling)
    return TerminalProfile(signals=signals, render_profile=resolved)
