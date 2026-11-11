# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Registre de la zone neutre : `<zone>/registre.json` (format `omega-registre`, version 1).

Contenu fixe a l'etape 3 (spec ~/DEV/CONNECT/SPEC_ETAPE3_OMEGA_CONNECT_PLOMBERIE.md, lot D). omega-connect en
est le seul ecrivain ; les outils et l'utilisateur le lisent (groupe omega-synchro).

Le registre dit ce qu'omega-connect a CREE (groupe, dossiers, membres du groupe, groupe donne a un service) et QUAND, et quelles
installations il a reliees : `retirer` ne defait que ce qui y figure. Aucun chemin de fichier copie n'y est
ecrit : les copies se deduisent de l'identifiant (`jetons/<id>.json`, `fiches/<id>.json`), pour qu'un registre
modifie a la main ne puisse jamais designer un autre fichier a supprimer."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from omega_lib.synchro.codec import _date, _guard, _header_dict, _Invalid, _text
from omega_lib.synchro.constants import FORMAT_REGISTRY, ZONE_SHEETS_DIR, ZONE_TOKENS_DIR
from omega_lib.synchro.models import ReadResult
from omega_lib.synchro.policies import is_absolute_clean_path, is_installation_id, is_name


class ZoneState(str, Enum):
    ACTIVE = "active"
    """omega-connect tient la zone a jour."""
    FROZEN = "frozen"
    """Zone gardee, liens figes : plus personne ne synchronise (omega-connect retire, zone conservee)."""


class CreatedKind(str, Enum):
    GROUP = "group"
    DIRECTORY = "directory"
    MEMBER = "member"
    """Compte ajoute au groupe de la zone par omega-connect."""
    SERVICE_GROUP = "service-group"
    """Service systemd d'un outil a qui l'outil lui-meme a donne le groupe de la zone, a la demande
    d'omega-connect (complement `<service>.service.d/omega-synchro.conf`, voir `synchro.service_group`) :
    a retirer avant le groupe, sinon le service ne demarre plus."""


@dataclass(frozen=True)
class CreatedItem:
    kind: CreatedKind
    target: str
    """Nom du groupe, chemin absolu du dossier, nom du compte ajoute au groupe, ou nom du service (sans
    `.service`)."""
    at: str


@dataclass(frozen=True)
class LinkedInstallation:
    installation_id: str
    tool: str
    instance: str
    root: str
    owner: str
    version: str
    linked_at: str
    has_sheet: bool = False
    """Une copie de la fiche existe dans `fiches/` (outils qui en produisent une)."""

    @property
    def token_file(self) -> str:
        return token_copy_name(self.installation_id)

    @property
    def sheet_file(self) -> str:
        return sheet_copy_name(self.installation_id) if self.has_sheet else ""


@dataclass(frozen=True)
class ZoneRegistry:
    zone: str
    state: ZoneState
    updated_at: str
    created: tuple[CreatedItem, ...] = ()
    installations: tuple[LinkedInstallation, ...] = ()

    def created_items(self, kind: CreatedKind) -> tuple[CreatedItem, ...]:
        return tuple(item for item in self.created if item.kind is kind)

    def installation(self, installation_id: str) -> LinkedInstallation | None:
        return next((item for item in self.installations if item.installation_id == installation_id), None)


def token_copy_name(installation_id: str) -> str:
    """Chemin relatif a la zone de la copie d'un jeton (`jetons/<id>.json`)."""
    if not is_installation_id(installation_id):
        raise ValueError("invalid installation id")
    return f"{ZONE_TOKENS_DIR}/{installation_id}.json"


def sheet_copy_name(installation_id: str) -> str:
    if not is_installation_id(installation_id):
        raise ValueError("invalid installation id")
    return f"{ZONE_SHEETS_DIR}/{installation_id}.json"


def registry_to_dict(registry: ZoneRegistry) -> dict[str, Any]:
    return {
        **_header_dict(FORMAT_REGISTRY),
        "zone": registry.zone, "state": registry.state.value, "updated_at": registry.updated_at,
        "created": [{"kind": item.kind.value, "target": item.target, "at": item.at} for item in registry.created],
        "installations": [
            {"installation_id": item.installation_id, "tool": item.tool, "instance": item.instance,
             "root": item.root, "owner": item.owner, "version": item.version, "linked_at": item.linked_at,
             "has_sheet": item.has_sheet}
            for item in registry.installations
        ],
    }


def _created(raw: object) -> CreatedItem:
    if not isinstance(raw, dict):
        raise _Invalid("created entries must be objects")
    try:
        kind = CreatedKind(raw.get("kind"))
    except ValueError as error:
        raise _Invalid("created.kind is unknown") from error
    target = _text(raw, "target")
    if kind is CreatedKind.DIRECTORY and not is_absolute_clean_path(target):
        raise _Invalid("created directory must be an absolute clean path")
    if kind is not CreatedKind.DIRECTORY and not is_name(target):
        raise _Invalid("created group or member must be a name")
    return CreatedItem(kind, target, _date(raw, "at"))


def _linked(raw: object) -> LinkedInstallation:
    if not isinstance(raw, dict):
        raise _Invalid("installations entries must be objects")
    installation_id = raw.get("installation_id")
    if not is_installation_id(installation_id):
        raise _Invalid("installation_id must be 32 lowercase hexadecimal characters")
    tool, instance = _text(raw, "tool"), _text(raw, "instance")
    if not is_name(tool) or not is_name(instance):
        raise _Invalid("tool and instance must be names")
    root = _text(raw, "root")
    if not is_absolute_clean_path(root):
        raise _Invalid("root must be an absolute clean path")
    has_sheet = raw.get("has_sheet", False)
    if not isinstance(has_sheet, bool):
        raise _Invalid("has_sheet must be a boolean")
    return LinkedInstallation(
        installation_id=str(installation_id), tool=tool, instance=instance, root=root,
        owner=_text(raw, "owner", required=False), version=_text(raw, "version", required=False),
        linked_at=_date(raw, "linked_at"), has_sheet=has_sheet)


def _build_registry(data: dict[str, Any]) -> ZoneRegistry:
    zone = _text(data, "zone")
    if not is_absolute_clean_path(zone):
        raise _Invalid("zone must be an absolute clean path")
    try:
        state = ZoneState(data.get("state"))
    except ValueError as error:
        raise _Invalid("state is unknown") from error
    created_raw, installations_raw = data.get("created", []), data.get("installations", [])
    if not isinstance(created_raw, list) or not isinstance(installations_raw, list):
        raise _Invalid("created and installations must be lists")
    installations = tuple(_linked(item) for item in installations_raw)
    if len({item.installation_id for item in installations}) != len(installations):
        raise _Invalid("installations must not repeat an installation_id")
    return ZoneRegistry(zone=zone, state=state, updated_at=_date(data, "updated_at"),
                        created=tuple(_created(item) for item in created_raw), installations=installations)


def registry_from_dict(data: object) -> ReadResult[ZoneRegistry]:
    return _guard(data, FORMAT_REGISTRY, _build_registry)
