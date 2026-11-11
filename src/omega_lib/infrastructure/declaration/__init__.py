# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Adaptateurs de « Contact et support » : envoi HTTPS, stockage JSON, lecture de sha.txt
(bibliotheque standard seulement, urllib). Assemblage pour un outil : `build_contact_support`."""
from __future__ import annotations

from pathlib import Path

from omega_lib.infrastructure.declaration.https_release_source import HttpsReleaseSource
from omega_lib.infrastructure.declaration.https_sender import HttpsDeclarationSender
from omega_lib.infrastructure.declaration.json_store import JsonDeclarationStore
from omega_lib.ports.declaration import ContactSupportServices

DECLARATION_FILENAME = "declaration.json"
"""Sous le dossier var/ de l'outil ; a exclure de l'archive livree (build-release.sh)."""


def build_contact_support(software: str, version: str, var_dir: Path) -> ContactSupportServices:
    """Adaptateurs reels : `<var_dir>/declaration.json`, reception et site kraynux en HTTPS."""
    from omega_lib.infrastructure.desktop.browser_opener import open_url

    return ContactSupportServices(
        software=software, version=version,
        store=JsonDeclarationStore(var_dir / DECLARATION_FILENAME),
        sender=HttpsDeclarationSender(software, version),
        release_source=HttpsReleaseSource(software, version),
        open_url=open_url,
    )
