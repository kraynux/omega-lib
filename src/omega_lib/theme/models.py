# Copyright (c) 2026 kraynux - Licence MIT
"""Entite representant l'etat d'un theme applique.

Porte depuis omega-scan/omega-stress dans omega-lib (D-008, 2026-08-29) :
catalogue et logique de resolution identiques dans les 2 tools deja finis,
candidat naturel a la mutualisation plutot qu'une 3e copie."""
from __future__ import annotations

from dataclasses import dataclass

from omega_lib.terminal.models import RenderProfile


@dataclass(frozen=True, slots=True)
class AppliedTheme:
    """Theme effectivement applique a l'interface : nom retenu, profil de
    rendu courant, et repli eventuel si le theme demande etait inconnu."""

    theme_name: str
    render_profile: RenderProfile
    fell_back_from: str | None = None
