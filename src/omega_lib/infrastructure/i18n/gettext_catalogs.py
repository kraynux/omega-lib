# Copyright (c) 2026 kraynux - Licence MIT
"""Catalogues de traduction sur disque (fichiers .mo de gettext).

Disposition standard : <locale_dir>/<code>/LC_MESSAGES/<domaine>.mo. Une langue est
proposee des que son fichier existe (plan i18n D11 : ajouter une langue = deposer un fichier).
Statut lu dans l'en-tete du catalogue : `X-Omega-Status: validated` (sinon "en test")."""
from __future__ import annotations

import gettext
from pathlib import Path

from omega_lib.i18n.models import LanguageStatus
from omega_lib.i18n.policies import PSEUDO_LANGUAGE_CODE, SOURCE_LANGUAGE_CODE
from omega_lib.i18n.service import PseudoTranslations

_STATUS_HEADER = "x-omega-status"


class CatalogError(Exception):
    """Catalogue present mais illisible (fichier corrompu, droits)."""


def _catalog_path(locale_dir: Path, domain: str, code: str) -> Path:
    return locale_dir / code / "LC_MESSAGES" / f"{domain}.mo"


def discover_catalogs(locale_dir: Path, domain: str) -> dict[str, LanguageStatus]:
    """Langues dont le catalogue est present. Un catalogue illisible est quand meme
    liste (statut "en test") : son chargement echouera proprement et l'interface
    repartira en langue source avec un message."""
    found: dict[str, LanguageStatus] = {}
    if not locale_dir.is_dir():
        return found
    for entry in sorted(locale_dir.iterdir()):
        if entry.name in (SOURCE_LANGUAGE_CODE, PSEUDO_LANGUAGE_CODE):
            continue
        path = _catalog_path(locale_dir, domain, entry.name)
        if not path.is_file():
            continue
        try:
            with path.open("rb") as handle:
                info = gettext.GNUTranslations(handle).info()
            status_text = info.get(_STATUS_HEADER, "").strip().lower()
        except (OSError, ValueError, UnicodeDecodeError):
            status_text = ""
        found[entry.name] = LanguageStatus.VALIDATED if status_text == "validated" else LanguageStatus.TESTING
    return found


def load_translations(locale_dir: Path, domain: str, code: str) -> gettext.NullTranslations | None:
    """None pour la langue source. Langue de controle generee a la volee. Sinon le catalogue
    du disque ; CatalogError s'il est absent ou illisible (jamais une exception brute)."""
    if code == SOURCE_LANGUAGE_CODE:
        return None
    if code == PSEUDO_LANGUAGE_CODE:
        return PseudoTranslations()
    path = _catalog_path(locale_dir, domain, code)
    try:
        with path.open("rb") as handle:
            return gettext.GNUTranslations(handle)
    except FileNotFoundError as e:
        raise CatalogError(f"catalogue absent : {path}") from e
    except (OSError, ValueError, UnicodeDecodeError) as e:
        raise CatalogError(f"catalogue illisible : {path} ({e})") from e


SHARED_DOMAIN = "omega-lib"
"""Catalogue partage (OMEGA-SUITE_PLAN-DETAILLE_I18N.md Q3) : les phrases communes a plusieurs
outils omega, traduites une seule fois. Livre avec omega-lib (vendore par chaque outil)."""

SHARED_LOCALE_DIR = Path(__file__).resolve().parents[2] / "locale"
"""src/omega_lib/locale/<code>/LC_MESSAGES/omega-lib.mo"""


def discover_tool_catalogs(locale_dir: Path, domain: str,
                           shared_dir: Path = SHARED_LOCALE_DIR) -> dict[str, LanguageStatus]:
    """Langues proposees pour un outil : son catalogue OU le catalogue partage suffit (une
    phrase absente des deux reste en francais, plan D9). Statut : celui du catalogue de
    l'outil s'il existe, sinon celui du catalogue partage."""
    found = discover_catalogs(shared_dir, SHARED_DOMAIN)
    found.update(discover_catalogs(locale_dir, domain))
    return found


def load_tool_translations(locale_dir: Path, domain: str, code: str,
                           shared_dir: Path = SHARED_LOCALE_DIR) -> gettext.NullTranslations | None:
    """Catalogue de l'outil chaine au catalogue partage : la traduction propre de l'outil
    l'emporte toujours (un contexte different peut demander un autre mot). None pour la
    langue source ; CatalogError si aucun des deux n'existe ou si l'un est illisible."""
    if code in (SOURCE_LANGUAGE_CODE, PSEUDO_LANGUAGE_CODE):
        return load_translations(locale_dir, domain, code)
    own_exists = _catalog_path(locale_dir, domain, code).is_file()
    shared_exists = _catalog_path(shared_dir, SHARED_DOMAIN, code).is_file()
    if not own_exists and not shared_exists:
        raise CatalogError(f"catalogue absent : {_catalog_path(locale_dir, domain, code)}")
    shared = load_translations(shared_dir, SHARED_DOMAIN, code) if shared_exists else None
    if not own_exists:
        return shared
    own = load_translations(locale_dir, domain, code)
    if own is not None and shared is not None:
        own.add_fallback(shared)
    return own
