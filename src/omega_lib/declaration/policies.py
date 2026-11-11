# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Regles de « Contact et support » (pur, aucune I/O) : message de declaration, retrait,
comparaison de version avec la liste publiee (download/sha.txt du site)."""
from __future__ import annotations

import re

from omega_lib.declaration.countries import COUNTRY_CODES
from omega_lib.declaration.models import (
    CONTINENTS,
    MODE_ONCE,
    OTHER,
    SITE_URL,
    SOFTWARES,
    Declaration,
    UpdateCheck,
    UpdateStatus,
)

_KEY = re.compile(r"^[0-9a-f]{32}$")
_VERSION = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}$")
_NUMERIC_VERSION = re.compile(r"^\d{1,3}(?:\.\d{1,3}){0,3}$")


def declaration_errors(declaration: Declaration) -> list[str]:
    """Noms des champs invalides ; liste vide si la declaration est envoyable telle quelle."""
    errors = []
    if not _KEY.match(declaration.key):
        errors.append("cle")
    if declaration.continent and declaration.continent not in (*CONTINENTS, OTHER):
        errors.append("continent")
    if declaration.country and declaration.country not in (*COUNTRY_CODES, OTHER):
        errors.append("pays")
    return errors


def wire_version(version: str) -> str:
    """Version au format de la reception (`X.Y.Z`) : « 3.5 » (omega-fire) -> « 3.5.0 ». Une version
    non numerique ou trop longue donne « 0.0.0 » (la reception refuserait sinon tout le message)."""
    version = version.strip()
    if not _NUMERIC_VERSION.match(version):
        return "0.0.0"
    parts = version.split(".")
    if len(parts) > 3:
        return "0.0.0"
    return ".".join([*parts, *["0"] * (3 - len(parts))])


def is_valid_version(version: str) -> bool:
    return bool(_VERSION.match(version))


def build_payload(declaration: Declaration, software: str, version: str) -> dict[str, str]:
    """Le message exact envoye (et affiche avant l'envoi). Continent et pays absents s'ils ne sont
    pas choisis."""
    if software not in SOFTWARES:
        raise ValueError(f"logiciel inconnu de la reception : {software}")
    payload = {"cle": declaration.key, "logiciel": software, "version": wire_version(version), "envoi": MODE_ONCE}
    if declaration.continent:
        payload["continent"] = declaration.continent
    if declaration.country:
        payload["pays"] = declaration.country
    return payload


def build_withdrawal(key: str) -> dict[str, object]:
    """« Ne plus me declarer » : la reception supprime l'entree (204, meme si la cle est inconnue)."""
    return {"cle": key, "retrait": True}


# ------------------------------------------------------------------------------ mises a jour
def download_base_url(software: str) -> str:
    """Dossier des archives publiees : https://.../omega-scan/download/ (STRUCTURE_PUBLICATION_OMEGA.md)."""
    return f"{SITE_URL}{software}/download/"


def sha_list_url(software: str) -> str:
    return download_base_url(software) + "sha.txt"


def version_key(version: str) -> tuple[int, ...] | None:
    """« 2.6.0 » -> (2, 6, 0) ; « 3.5 » -> (3, 5, 0) (comparables entre elles) ; None si ce n'est
    pas une version numerique."""
    parts = version.strip().split(".")
    if not parts or not all(part.isdigit() for part in parts):
        return None
    numbers = [int(part) for part in parts]
    while len(numbers) < 3:
        numbers.append(0)
    return tuple(numbers)


def published_versions(software: str, sha_list: str) -> list[str]:
    """Versions des archives citees dans sha.txt (`<empreinte>  omega-scan-1.5.0.tar.gz`), sans
    doublon, de la plus haute a la plus basse. Les anciens noms (« omega-fire-v3.0 ») sont ignores."""
    pattern = re.compile(re.escape(software) + r"-(\d+(?:\.\d+){1,3})\.tar\.gz")
    found = {match.group(1) for match in pattern.finditer(sha_list)}
    return sorted(found, key=lambda version: version_key(version) or (), reverse=True)


def compare_with_published(software: str, installed: str, sha_list: str | None) -> UpdateCheck:
    installed_key = version_key(installed)
    versions = published_versions(software, sha_list) if sha_list else []
    if installed_key is None or not versions:
        return UpdateCheck(UpdateStatus.UNKNOWN, installed)
    latest = versions[0]
    latest_key = version_key(latest) or ()
    base = download_base_url(software)
    archive_url = f"{base}{software}-{latest}.tar.gz"
    notes_url = f"{base}{software}-{latest}-nouveautes.txt"
    if latest_key > installed_key:
        return UpdateCheck(UpdateStatus.UPDATE_AVAILABLE, installed, latest, archive_url, notes_url)
    if latest_key < installed_key:
        return UpdateCheck(UpdateStatus.AHEAD, installed, latest, archive_url, notes_url)
    return UpdateCheck(UpdateStatus.UP_TO_DATE, installed, latest, archive_url, notes_url)
