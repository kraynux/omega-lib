# Copyright (c) 2026 kraynux - Licence MIT
"""Decision de repli et de degradation d'un theme.
Porte depuis omega-scan/omega-stress dans omega-lib (D-008)."""
from __future__ import annotations

from omega_lib.terminal.models import RenderProfile
from omega_lib.theme.models import AppliedTheme
from omega_lib.theme.policies import (
    DEFAULT_TUI_THEME,
    TUI_THEMES,
    Palette,
    mono_palette,
    reduced_palette,
)


def resolve_applied_theme(requested_theme: str, render_profile: RenderProfile) -> AppliedTheme:
    """Resout le theme effectivement applique : repli vers le theme par
    defaut si le nom demande est inconnu du catalogue. Ne juge jamais de la
    compatibilite couleur du terminal — deja couvert par terminal/service.py,
    qui decide render_profile independamment du choix de theme."""
    fell_back_from: str | None = None
    theme_name = requested_theme
    if theme_name not in TUI_THEMES:
        fell_back_from = requested_theme
        theme_name = DEFAULT_TUI_THEME

    return AppliedTheme(theme_name=theme_name, render_profile=render_profile, fell_back_from=fell_back_from)


def resolve_palette(theme_name: str, render_profile: RenderProfile) -> Palette:
    """Retourne la palette a utiliser pour un theme et un profil de rendu
    donnes, en appliquant la degradation generique si necessaire."""
    definition = TUI_THEMES.get(theme_name, TUI_THEMES[DEFAULT_TUI_THEME])
    if render_profile is RenderProfile.MONO:
        return mono_palette(definition.palette)
    if render_profile is RenderProfile.REDUCED:
        return reduced_palette(definition.palette)
    return definition.palette
