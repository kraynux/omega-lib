# Copyright (c) 2026 kraynux - Licence MIT
"""Entites du sous-domaine terminal : signaux bruts et profil de rendu resolu.

Porte depuis omega-scan/omega-stress dans omega-lib (D-008, 2026-08-29)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RenderProfile(str, Enum):
    """Niveau de complexite structurelle affiche par le TUI, decide depuis
    la capacite terminal detectee (distinct du choix de theme de couleur)."""

    COMPLETE = "complete"
    STANDARD = "standard"
    REDUCED = "reduced"
    MONO = "mono"


@dataclass(frozen=True, slots=True)
class TerminalSignals:
    """Signaux bruts remontes par infrastructure/terminal/raw_capabilities.py
    — aucune decision ici, uniquement des faits observes."""

    family: str
    columns: int
    rows: int
    is_ssh: bool = False


@dataclass(frozen=True, slots=True)
class TerminalProfile:
    """Resultat de la decision prise par terminal/service.py::
    resolve_render_profile a partir de TerminalSignals."""

    signals: TerminalSignals
    render_profile: RenderProfile
