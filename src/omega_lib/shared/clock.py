# Copyright (c) 2026 kraynux - Licence MIT
"""Horloge de production, utilisee a la frontiere presentation/application.

Porte verbatim depuis omega_scan.shared.clock (memes conventions dans
toute la suite) — voir ~/DEV/SUITE/DECISIONS_ARCHITECTURE.md D-005.
"""
from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Heure courante en UTC. Implementation de production par defaut —
    domain/ et application/ ne l'appellent jamais elles-memes, elles
    recoivent toujours `now` explicitement en parametre."""
    return datetime.now(timezone.utc)
