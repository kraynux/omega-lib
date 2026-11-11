# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Modeles des contrats d'interconnexion (spec etape 2, §3 a §6). Valeurs ASCII, jamais traduites."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class ReadStatus(str, Enum):
    """Issue d'une lecture (spec §2.8) ; alimente les etats de lien (actif, degrade, absent, casse)."""

    OK = "ok"
    ABSENT = "absent"
    UNREADABLE = "unreadable"
    """Droits insuffisants ou erreur d'entree-sortie."""
    INVALID = "invalid"
    """JSON casse, champ obligatoire manquant ou mal type, format inattendu."""
    INCOMPATIBLE = "incompatible"
    """Version plus haute que celle que ce code sait lire."""


@dataclass(frozen=True)
class ReadResult(Generic[T]):
    status: ReadStatus
    value: T | None = None
    detail: str = ""
    """Raison courte, en anglais ASCII (journal technique, jamais affichee telle quelle)."""

    @property
    def ok(self) -> bool:
        return self.status is ReadStatus.OK


class CapabilityState(str, Enum):
    ABSENT = "absent"
    DISABLED = "disabled"
    ACTIVE = "active"
    UNKNOWN = "unknown"
    """Non verifiable par ce compte (fiche partielle)."""


class BanAction(str, Enum):
    BAN = "ban"
    UNBAN = "unban"


@dataclass(frozen=True)
class InstallToken:
    """Jeton d'installation : `<racine>/var/omega-jeton.json` (spec §3)."""

    tool: str
    version: str
    installation_id: str
    machine: str
    root: str
    owner: str
    installed_at: str
    updated_at: str
    contracts: Mapping[str, tuple[int, ...]] = field(default_factory=dict)
    offers: tuple[str, ...] = ()
    wants: tuple[str, ...] = ()


@dataclass(frozen=True)
class ServiceInfo:
    manager: str
    """systemd, openrc, runit, ou "none"."""
    unit: str = ""
    user: str = ""
    group: str = ""
    state: str = ""
    """Etat brut du gestionnaire (active, inactive, failed...) ; vide si inconnu."""


@dataclass(frozen=True)
class SharedFile:
    path: str
    contract: tuple[str, int] | None = None


@dataclass(frozen=True)
class InstanceSheet:
    """Fiche d'instance (spec §4) : produite par la CLI de l'outil, copiee par omega-connect."""

    tool: str
    version: str
    installation_id: str
    instance: str
    generated_at: str
    capabilities: Mapping[str, CapabilityState] = field(default_factory=dict)
    service: ServiceInfo | None = None
    files: Mapping[str, SharedFile] = field(default_factory=dict)
    partial: bool = False
    extra: Mapping[str, Any] = field(default_factory=dict)
    """Rubriques propres a l'outil (exposure, omega_waf, backends...), ecrites au premier niveau."""


@dataclass(frozen=True)
class BanEvent:
    """Une ligne de `bans/journal.jsonl`, ou une entree de `bans/actifs.json` (spec §6)."""

    id: str
    at: str
    action: BanAction
    network: str
    origin: str
    jail: str = ""
    expires_at: str | None = None
    """None = permanent (sur un ban) ; sans objet sur une levee."""
    reason: str = ""
    host: str = ""


@dataclass(frozen=True)
class ActiveBans:
    updated_at: str
    entries: tuple[BanEvent, ...] = ()
