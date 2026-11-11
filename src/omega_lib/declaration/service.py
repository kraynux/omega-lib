# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Cas d'usage de « Contact et support » (repris d'omega-log, application/use_cases/declaration.py).

- `declare` : au clic « Envoyer » (ou `declaration declare --yes`). Rien n'est enregistre si
  l'envoi echoue ; jamais d'envoi automatique.
- `withdraw` : « Ne plus me declarer ». Le retrait est envoye, puis la declaration est effacee
  localement, meme si la reception est injoignable (l'entree y disparaitra seule apres 1 an).
- `check_for_update` : lit download/sha.txt du site, rien n'est envoye."""
from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from omega_lib.declaration.models import Declaration, UpdateCheck
from omega_lib.declaration.policies import (
    build_payload,
    build_withdrawal,
    compare_with_published,
    declaration_errors,
)
from omega_lib.ports.declaration import (
    DeclarationSender,
    DeclarationStore,
    ReleaseSource,
    StoredDeclaration,
)


def new_key() -> str:
    """128 bits tires au hasard (module secrets) : ne derive de rien (ni MAC, ni nom de machine)."""
    return secrets.token_hex(16)


def preview_payload(store: DeclarationStore, software: str, version: str, continent: str,
                    country: str) -> dict[str, str]:
    """Message exact affiche avant l'envoi. Cle encore inexistante : sa forme seulement."""
    existing = store.load()
    key = existing.declaration.key if existing is not None else "0" * 32
    return build_payload(Declaration(key, continent, country), software, version)


@dataclass(frozen=True)
class DeclareResult:
    ok: bool
    reason: str = ""


def declare(
    store: DeclarationStore, sender: DeclarationSender, software: str, version: str,
    continent: str = "", country: str = "", *, key_factory: Callable[[], str] = new_key,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> DeclareResult:
    existing = store.load()
    declaration = Declaration(existing.declaration.key if existing is not None else key_factory(),
                              continent, country)
    errors = declaration_errors(declaration)
    if errors:
        raise ValueError(", ".join(errors))
    outcome = sender.send(dict(build_payload(declaration, software, version)))
    if not outcome.ok:
        return DeclareResult(ok=False, reason=outcome.reason)
    store.save(StoredDeclaration(declaration, existing.declared_at if existing is not None else now()))
    return DeclareResult(ok=True)


@dataclass(frozen=True)
class WithdrawResult:
    was_declared: bool
    reception_reached: bool


def withdraw(store: DeclarationStore, sender: DeclarationSender) -> WithdrawResult:
    existing = store.load()
    if existing is None:
        return WithdrawResult(was_declared=False, reception_reached=False)
    outcome = sender.send(build_withdrawal(existing.declaration.key))
    store.delete()
    return WithdrawResult(was_declared=True, reception_reached=outcome.ok)


def check_for_update(source: ReleaseSource, software: str, installed: str) -> UpdateCheck:
    return compare_with_published(software, installed, source.fetch_sha_list())
