# Copyright (c) 2026 kraynux - Licence MIT
"""Langue imposee par l'hote (OMEGA-SUITE_PLAN-DETAILLE_I18N.md Q2) - pur, sans I/O.

Dans omega-suite, les 7 outils tournent dans le MEME processus que la suite : un seul
selecteur (les Reglages de la suite) decide pour tous. La suite fixe ici la langue AVANT
d'importer le moindre ecran d'outil ; chaque outil la lit en premier, avant sa variable
d'environnement et son propre reglage, et masque alors son selecteur de langue.
Lance seul, un outil ne trouve aucune langue d'hote et garde son propre reglage."""
from __future__ import annotations

from collections.abc import Callable

_host: tuple[str, str] | None = None
_export_provider: Callable[[], str] | None = None


def set_host_language(code: str, host: str) -> None:
    """`code` : langue DEFINITIVE de la session (repli console deja applique par l'hote).
    `host` : nom affiche de l'hote (\"omega-suite\")."""
    global _host
    _host = (code, host)


def clear_host_language() -> None:
    global _host, _export_provider
    _host = None
    _export_provider = None


def host_language() -> str | None:
    """Langue imposee par l'hote, ou None quand l'outil est lance seul."""
    return None if _host is None else _host[0]


def host_name() -> str | None:
    return None if _host is None else _host[1]


def set_host_export_language(provider: Callable[[], str] | None) -> None:
    """Langue des exports imposee par l'hote (lot N, Q5 : un seul reglage dans la suite).
    `provider` est relu a CHAQUE export (effet immediat d'un changement de reglage) et rend un
    code de langue, ou "" pour « comme l'interface ». None : plus d'hote."""
    global _export_provider
    _export_provider = provider


def host_export_language() -> str | None:
    """Langue des exports choisie par l'hote ("" = comme l'interface), ou None quand l'outil est
    lance seul (il lit alors son propre reglage)."""
    return None if _export_provider is None else _export_provider()
