# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Jeton d'installation `<racine>/var/omega-jeton.json` (spec etape 2, §3).

Ecrit par l'outil lui-meme, a l'installation et a chaque lancement si quelque chose a change ;
toujours sous le compte proprietaire du dossier, jamais en root. Ne leve jamais d'exception : un jeton
impossible a ecrire laisse simplement l'outil « non relie »."""
from __future__ import annotations

import os
import pwd
import secrets
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from omega_lib.infrastructure.synchro.files import read_contract, write_json_atomic
from omega_lib.synchro.codec import token_from_dict, token_to_dict
from omega_lib.synchro.constants import MACHINE_ID_PATHS, TOKEN_FILE_MODE, TOKEN_RELATIVE_PATH
from omega_lib.synchro.models import InstallToken, ReadResult, ReadStatus
from omega_lib.synchro.policies import (
    TokenDecision,
    TokenSituation,
    format_utc,
    machine_fingerprint,
    token_decision,
)


@dataclass(frozen=True)
class TokenRefresh:
    outcome: str
    """created, new_id, updated, unchanged, skipped."""
    path: Path
    token: InstallToken | None = None
    reason: str = ""


def token_path(root: Path) -> Path:
    return root / TOKEN_RELATIVE_PATH


def read_install_token(root: Path) -> ReadResult[InstallToken]:
    return read_contract(token_path(root), token_from_dict)


def read_machine_fingerprint(paths: Iterable[str] = MACHINE_ID_PATHS) -> str:
    for candidate in paths:
        try:
            text = Path(candidate).read_text(encoding="ascii", errors="replace")
        except OSError:
            continue
        if text.strip():
            return machine_fingerprint(text)
    return ""


def _owner_name(uid: int) -> str:
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return str(uid)


def _old_root_has_same_id(existing: InstallToken, root: Path) -> bool:
    old_root = Path(existing.root)
    try:
        if old_root.resolve() == root:
            return False
    except OSError:
        return False
    other = read_install_token(old_root)
    return other.ok and other.value is not None and other.value.installation_id == existing.installation_id


def refresh_install_token(
    root: Path,
    tool: str,
    version: str,
    *,
    contracts: Mapping[str, Iterable[int]] | None = None,
    offers: Iterable[str] = (),
    wants: Iterable[str] = (),
    now: datetime | None = None,
    machine: str | None = None,
    euid: int | None = None,
) -> TokenRefresh:
    path = token_path(root)
    try:
        real_root = root.resolve()
        owner_uid = real_root.stat().st_uid
    except OSError as error:
        return TokenRefresh("skipped", path, reason=f"root not readable: {error.strerror}")
    path = token_path(real_root)
    effective = os.geteuid() if euid is None else euid
    if effective == 0:
        return TokenRefresh("skipped", path, reason="never written as root")
    if effective != owner_uid:
        return TokenRefresh("skipped", path, reason="only the owner of the directory writes the token")

    current = read_install_token(real_root)
    if current.status in (ReadStatus.UNREADABLE, ReadStatus.INCOMPATIBLE):
        # Illisible : ne pas ecraser ce qu'on ne voit pas. Plus recent : ne pas le degrader.
        return TokenRefresh("skipped", path, reason=f"existing token {current.status.value}: {current.detail}")
    existing = current.value if current.ok else None

    situation = TokenSituation(
        tool=tool, version=version, root=str(real_root), owner=_owner_name(owner_uid),
        machine=read_machine_fingerprint() if machine is None else machine,
        old_root_still_has_same_id=existing is not None and _old_root_has_same_id(existing, real_root),
    )
    decision = token_decision(existing, situation)
    wanted_contracts = {name: tuple(versions) for name, versions in (contracts or {}).items()}
    wanted_offers, wanted_wants = tuple(offers), tuple(wants)
    if decision is TokenDecision.KEEP and existing is not None and (
            dict(existing.contracts), existing.offers, existing.wants) != (wanted_contracts, wanted_offers, wanted_wants):
        decision = TokenDecision.UPDATE
    if decision is TokenDecision.KEEP:
        return TokenRefresh("unchanged", path, existing)

    stamp = format_utc(now or datetime.now(timezone.utc))
    fresh = decision in (TokenDecision.CREATE, TokenDecision.NEW_ID) or existing is None
    token = InstallToken(
        tool=tool, version=version,
        installation_id=secrets.token_hex(16) if fresh else existing.installation_id,  # type: ignore[union-attr]
        machine=situation.machine, root=situation.root, owner=situation.owner,
        installed_at=stamp if fresh else existing.installed_at,  # type: ignore[union-attr]
        updated_at=stamp, contracts=wanted_contracts, offers=wanted_offers, wants=wanted_wants,
    )
    try:
        path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        write_json_atomic(path, token_to_dict(token), TOKEN_FILE_MODE)
    except OSError as error:
        return TokenRefresh("skipped", path, reason=f"write failed: {error.strerror}")
    outcome = {TokenDecision.CREATE: "created", TokenDecision.NEW_ID: "new_id"}.get(decision, "updated")
    return TokenRefresh(outcome, path, token)
