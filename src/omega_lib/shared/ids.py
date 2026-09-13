# Copyright (c) 2026 kraynux - Licence MIT
"""Generation d'identifiants opaques.

Porte depuis omega_scan.shared.ids, simplifie : le prefixe "scan-" de
omega-scan etait un artefact de compatibilite avec son propre format v1,
pas une convention generale de la suite. Ici, un seul generateur generique
en UUID4 — voir ~/DEV/SUITE/OMEGA-SUITE_ARBORESCENCE.md §6 (D-006) : tout
scan_id de la suite est un UUID, jamais un entier auto-increment local.
"""
from __future__ import annotations

import uuid


def new_id() -> str:
    """Identifiant opaque unique (hex UUID4), utilise pour toute entite
    creee cote application (scan_id, target_id, etc.)."""
    return uuid.uuid4().hex
