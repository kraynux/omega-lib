# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Regles pures des contrats d'interconnexion (spec etape 2, §2, §3.3, §6)."""
from __future__ import annotations

import hashlib
import ipaddress
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from omega_lib.synchro.models import InstallToken

ORIGIN_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,63}$")
"""Meme motif que la liste noire d'omega-serv (`--origin`, 2026-11-10)."""
RESERVED_ORIGINS = frozenset({"intervention"})
INSTALLATION_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
"""Nom d'outil, d'instance, de capacite, de contrat."""
RIPOSTE_JAIL_MARKER = "riposte"


def format_utc(moment: datetime) -> str:
    """ISO 8601 en UTC avec Z, a la seconde (`2026-11-10T14:03:00Z`)."""
    if moment.tzinfo is None:
        raise ValueError("naive datetime")
    return moment.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(text: object) -> datetime | None:
    """Date d'un contrat, ou None si absente, illisible ou sans fuseau."""
    if not isinstance(text, str) or not text:
        return None
    try:
        moment = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
    except ValueError:
        return None
    if moment.tzinfo is None:
        return None
    return moment.astimezone(timezone.utc)


def machine_fingerprint(machine_id: str) -> str:
    """Empreinte de `/etc/machine-id` (SHA-256 tronque a 16 hexadecimaux) : distingue deux machines
    sans publier l'identifiant lui-meme. Chaine vide si l'identifiant est inconnu."""
    cleaned = machine_id.strip()
    if not cleaned:
        return ""
    return hashlib.sha256(f"omega-synchro:{cleaned}".encode()).hexdigest()[:16]


def is_installation_id(value: object) -> bool:
    return isinstance(value, str) and bool(INSTALLATION_ID_PATTERN.match(value))


def is_name(value: object) -> bool:
    return isinstance(value, str) and bool(NAME_PATTERN.match(value))


def normalize_network(text: object) -> str | None:
    """Adresse ou reseau en notation CIDR normalisee (IPv4-mapped ramenee en IPv4), ou None."""
    if not isinstance(text, str) or not text.strip():
        return None
    try:
        network = ipaddress.ip_network(text.strip(), strict=False)
    except ValueError:
        return None
    if isinstance(network, ipaddress.IPv6Network) and network.network_address.ipv4_mapped is not None:
        mapped = network.network_address.ipv4_mapped
        prefix = max(network.prefixlen - 96, 0)
        return str(ipaddress.ip_network(f"{mapped}/{prefix}", strict=False))
    return str(network)


def validate_origin(origin: object) -> str | None:
    """None si l'origine est valide ; sinon la raison (anglais ASCII)."""
    if not isinstance(origin, str) or not ORIGIN_PATTERN.match(origin):
        return "origin must match " + ORIGIN_PATTERN.pattern
    if origin in RESERVED_ORIGINS:
        return f"origin {origin!r} is reserved"
    return None


def is_riposte_origin(origin: str, jail: str = "") -> bool:
    """Ban ne d'un jail RIPOSTE (escalade d'omega-serv lui-meme) : Active Defense l'ignore, sinon
    boucle (plan §10, test anti-boucle)."""
    tail = origin.split(":", 1)[1] if ":" in origin else ""
    return RIPOSTE_JAIL_MARKER in tail.split("-") or RIPOSTE_JAIL_MARKER in jail.split("-")


def is_absolute_clean_path(value: object) -> bool:
    """Chemin absolu sans `..` ni caractere de controle : seule forme acceptee dans un contrat."""
    if not isinstance(value, str) or not value.startswith("/") or "\x00" in value:
        return False
    if any(ord(ch) < 32 for ch in value):
        return False
    return ".." not in value.split("/")


class TokenDecision(str, Enum):
    CREATE = "create"
    """Aucun jeton lisible : en tirer un neuf."""
    NEW_ID = "new_id"
    """Dossier copie (autre machine, ou ancienne racine toujours presente) : nouvel identifiant."""
    UPDATE = "update"
    """Meme installation, version, racine ou proprietaire change : reecrire, meme identifiant."""
    KEEP = "keep"


@dataclass(frozen=True)
class TokenSituation:
    tool: str
    version: str
    root: str
    owner: str
    machine: str
    old_root_still_has_same_id: bool = False
    """Vrai si `existing.root` (ancienne racine) existe encore avec le meme identifiant : copie."""


def token_decision(existing: InstallToken | None, now_situation: TokenSituation) -> TokenDecision:
    """Spec §3.3 : machine differente -> nouvel identifiant ; racine differente -> deplacement (meme
    identifiant) sauf si l'ancienne racine porte encore le meme jeton (copie -> nouvel identifiant)."""
    if existing is None or existing.tool != now_situation.tool:
        return TokenDecision.CREATE
    if existing.machine and now_situation.machine and existing.machine != now_situation.machine:
        return TokenDecision.NEW_ID
    if existing.root != now_situation.root and now_situation.old_root_still_has_same_id:
        return TokenDecision.NEW_ID
    if (existing.root, existing.version, existing.owner, existing.machine) != (
        now_situation.root, now_situation.version, now_situation.owner, now_situation.machine,
    ):
        return TokenDecision.UPDATE
    return TokenDecision.KEEP
