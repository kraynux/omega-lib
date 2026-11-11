# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Conversion dict <-> modeles des contrats (spec etape 2, §2 a §6).

Lecture tolerante : `*_from_dict` ne leve jamais d'exception, elle rend un `ReadResult` (ok, invalid,
incompatible). Les champs inconnus sont ignores (ajout facultatif = meme version)."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, TypeVar

from omega_lib.synchro.constants import (
    FORMAT_ACTIVE_BANS,
    FORMAT_BAN,
    FORMAT_SHEET,
    FORMAT_TOKEN,
    SCHEMA_VERSIONS,
)
from omega_lib.synchro.models import (
    ActiveBans,
    BanAction,
    BanEvent,
    CapabilityState,
    InstallToken,
    InstanceSheet,
    ReadResult,
    ReadStatus,
    ServiceInfo,
    SharedFile,
)
from omega_lib.synchro.policies import (
    is_absolute_clean_path,
    is_installation_id,
    is_name,
    normalize_network,
    parse_utc,
    validate_origin,
)

T = TypeVar("T")

_SHEET_KEYS = frozenset({
    "format", "schema_version", "tool", "version", "installation_id", "instance", "generated_at",
    "capabilities", "service", "files", "partial",
})


class _Invalid(Exception):
    pass


def _header(data: object, expected_format: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise _Invalid("not a JSON object")
    if data.get("format") != expected_format:
        raise _Invalid(f"format is not {expected_format!r}")
    version = data.get("schema_version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise _Invalid("schema_version must be a positive integer")
    return data


def _guard(data: object, expected_format: str, build: Callable[[dict[str, Any]], T]) -> ReadResult[T]:
    try:
        checked = _header(data, expected_format)
        if checked["schema_version"] > SCHEMA_VERSIONS[expected_format]:
            return ReadResult(ReadStatus.INCOMPATIBLE, detail=(
                f"{expected_format} version {checked['schema_version']} > {SCHEMA_VERSIONS[expected_format]}"))
        return ReadResult(ReadStatus.OK, build(checked))
    except _Invalid as error:
        return ReadResult(ReadStatus.INVALID, detail=str(error))


def _text(data: Mapping[str, Any], key: str, *, required: bool = True) -> str:
    value = data.get(key, "")
    if not isinstance(value, str) or (required and not value):
        raise _Invalid(f"{key} must be a non-empty string" if required else f"{key} must be a string")
    return value


def _date(data: Mapping[str, Any], key: str) -> str:
    value = _text(data, key)
    if parse_utc(value) is None:
        raise _Invalid(f"{key} must be an ISO 8601 date with time zone")
    return value


def _names(data: Mapping[str, Any], key: str) -> tuple[str, ...]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(is_name(v) for v in value):
        raise _Invalid(f"{key} must be a list of names")
    return tuple(value)


def _header_dict(fmt: str) -> dict[str, Any]:
    return {"format": fmt, "schema_version": SCHEMA_VERSIONS[fmt]}


# --- Jeton d'installation -------------------------------------------------------------------------

def token_to_dict(token: InstallToken) -> dict[str, Any]:
    return {
        **_header_dict(FORMAT_TOKEN),
        "tool": token.tool, "version": token.version, "installation_id": token.installation_id,
        "machine": token.machine, "root": token.root, "owner": token.owner,
        "installed_at": token.installed_at, "updated_at": token.updated_at,
        "contracts": {name: list(versions) for name, versions in sorted(token.contracts.items())},
        "offers": list(token.offers), "wants": list(token.wants),
    }


def _build_token(data: dict[str, Any]) -> InstallToken:
    tool = _text(data, "tool")
    if not is_name(tool):
        raise _Invalid("tool must be a name")
    if not is_installation_id(data.get("installation_id")):
        raise _Invalid("installation_id must be 32 lowercase hexadecimal characters")
    root = _text(data, "root")
    if not is_absolute_clean_path(root):
        raise _Invalid("root must be an absolute path without '..'")
    contracts_raw = data.get("contracts", {})
    if not isinstance(contracts_raw, dict):
        raise _Invalid("contracts must be an object")
    contracts: dict[str, tuple[int, ...]] = {}
    for name, versions in contracts_raw.items():
        if not is_name(name) or not isinstance(versions, list) or not all(
                isinstance(v, int) and not isinstance(v, bool) and v >= 1 for v in versions):
            raise _Invalid("contracts must map names to lists of positive integers")
        contracts[name] = tuple(versions)
    return InstallToken(
        tool=tool, version=_text(data, "version"), installation_id=data["installation_id"],
        machine=_text(data, "machine", required=False), root=root, owner=_text(data, "owner"),
        installed_at=_date(data, "installed_at"), updated_at=_date(data, "updated_at"),
        contracts=contracts, offers=_names(data, "offers"), wants=_names(data, "wants"),
    )


def token_from_dict(data: object) -> ReadResult[InstallToken]:
    return _guard(data, FORMAT_TOKEN, _build_token)


# --- Fiche d'instance -----------------------------------------------------------------------------

def sheet_to_dict(sheet: InstanceSheet) -> dict[str, Any]:
    payload: dict[str, Any] = {
        **_header_dict(FORMAT_SHEET),
        "tool": sheet.tool, "version": sheet.version, "installation_id": sheet.installation_id,
        "instance": sheet.instance, "generated_at": sheet.generated_at,
        "capabilities": {name: state.value for name, state in sorted(sheet.capabilities.items())},
        "service": None if sheet.service is None else {
            "manager": sheet.service.manager, "unit": sheet.service.unit, "user": sheet.service.user,
            "group": sheet.service.group, "state": sheet.service.state,
        },
        "files": {
            name: {"path": item.path, "contract": None if item.contract is None else list(item.contract)}
            for name, item in sorted(sheet.files.items())
        },
        "partial": sheet.partial,
    }
    for key, value in sheet.extra.items():
        if key not in _SHEET_KEYS:
            payload[key] = value
    return payload


def _build_sheet(data: dict[str, Any]) -> InstanceSheet:
    tool = _text(data, "tool")
    if not is_name(tool):
        raise _Invalid("tool must be a name")
    installation_id = data.get("installation_id")
    if installation_id not in ("", None) and not is_installation_id(installation_id):
        raise _Invalid("installation_id must be 32 lowercase hexadecimal characters")
    capabilities_raw = data.get("capabilities", {})
    if not isinstance(capabilities_raw, dict):
        raise _Invalid("capabilities must be an object")
    capabilities: dict[str, CapabilityState] = {}
    for name, state in capabilities_raw.items():
        if not is_name(name):
            raise _Invalid("capability names must be names")
        try:
            capabilities[name] = CapabilityState(state)
        except ValueError:
            capabilities[name] = CapabilityState.UNKNOWN  # etat futur : tolere, affiche inconnu
    service_raw = data.get("service")
    service = None
    if service_raw is not None:
        if not isinstance(service_raw, dict):
            raise _Invalid("service must be an object or null")
        service = ServiceInfo(
            manager=_text(service_raw, "manager"), unit=_text(service_raw, "unit", required=False),
            user=_text(service_raw, "user", required=False), group=_text(service_raw, "group", required=False),
            state=_text(service_raw, "state", required=False),
        )
    files_raw = data.get("files", {})
    if not isinstance(files_raw, dict):
        raise _Invalid("files must be an object")
    files: dict[str, SharedFile] = {}
    for name, item in files_raw.items():
        if not is_name(name) or not isinstance(item, dict) or not is_absolute_clean_path(item.get("path")):
            raise _Invalid("files must map names to {path: absolute path}")
        contract = item.get("contract")
        if contract is not None:
            if (not isinstance(contract, list) or len(contract) != 2 or not is_name(contract[0])
                    or not isinstance(contract[1], int) or isinstance(contract[1], bool)):
                raise _Invalid("files.*.contract must be [name, version]")
            contract = (contract[0], contract[1])
        files[name] = SharedFile(item["path"], contract)
    partial = data.get("partial", False)
    if not isinstance(partial, bool):
        raise _Invalid("partial must be a boolean")
    instance = _text(data, "instance")
    if not is_name(instance):
        raise _Invalid("instance must be a name")
    return InstanceSheet(
        tool=tool, version=_text(data, "version"), installation_id=installation_id or "",
        instance=instance, generated_at=_date(data, "generated_at"), capabilities=capabilities,
        service=service, files=files, partial=partial,
        extra={k: v for k, v in data.items() if k not in _SHEET_KEYS},
    )


def sheet_from_dict(data: object) -> ReadResult[InstanceSheet]:
    return _guard(data, FORMAT_SHEET, _build_sheet)


# --- Evenements de ban et bans actifs -------------------------------------------------------------

def _event_fields(event: BanEvent) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": event.id, "at": event.at, "action": event.action.value, "network": event.network,
        "origin": event.origin, "jail": event.jail, "reason": event.reason, "host": event.host,
    }
    if event.action is BanAction.BAN:
        payload["expires_at"] = event.expires_at
    return payload


def ban_event_to_dict(event: BanEvent) -> dict[str, Any]:
    return {**_header_dict(FORMAT_BAN), **_event_fields(event)}


def _build_event(data: Mapping[str, Any]) -> BanEvent:
    event_id = _text(data, "id")
    if not is_name(event_id):
        raise _Invalid("id must be a name")
    try:
        action = BanAction(data.get("action"))
    except ValueError:
        raise _Invalid("action must be 'ban' or 'unban'") from None
    network = normalize_network(data.get("network"))
    if network is None:
        raise _Invalid("network must be an IP address or CIDR network")
    origin = data.get("origin")
    problem = validate_origin(origin)
    if problem:
        raise _Invalid(problem)
    expires_at = data.get("expires_at")
    if action is BanAction.BAN and expires_at is not None and parse_utc(expires_at) is None:
        raise _Invalid("expires_at must be null (permanent) or an ISO 8601 date")
    return BanEvent(
        id=event_id, at=_date(data, "at"), action=action, network=network, origin=str(origin),
        jail=_text(data, "jail", required=False), expires_at=expires_at if action is BanAction.BAN else None,
        reason=_text(data, "reason", required=False), host=_text(data, "host", required=False),
    )


def ban_event_from_dict(data: object) -> ReadResult[BanEvent]:
    return _guard(data, FORMAT_BAN, _build_event)


def active_bans_to_dict(active: ActiveBans) -> dict[str, Any]:
    return {**_header_dict(FORMAT_ACTIVE_BANS), "updated_at": active.updated_at,
            "entries": [_event_fields(entry) for entry in active.entries]}


def _build_active(data: dict[str, Any]) -> ActiveBans:
    entries_raw = data.get("entries", [])
    if not isinstance(entries_raw, list):
        raise _Invalid("entries must be a list")
    entries = []
    for item in entries_raw:
        if not isinstance(item, dict):
            raise _Invalid("entries must be objects")
        entry = _build_event(item)
        if entry.action is not BanAction.BAN:
            raise _Invalid("active bans only hold 'ban' entries")
        entries.append(entry)
    return ActiveBans(updated_at=_date(data, "updated_at"), entries=tuple(entries))


def active_bans_from_dict(data: object) -> ReadResult[ActiveBans]:
    return _guard(data, FORMAT_ACTIVE_BANS, _build_active)
