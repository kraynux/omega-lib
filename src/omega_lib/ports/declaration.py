# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Contrats de « Contact et support » (repris d'omega-log, sans le journal d'envois quotidiens
d'omega-serv : ces outils n'envoient qu'une fois, depuis l'ecran ou la ligne de commande)."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from omega_lib.declaration.models import Declaration


@dataclass(frozen=True)
class SendOutcome:
    ok: bool
    reason: str = ""
    """Vide si ok ; sinon « unreachable » (reseau, DNS, delai depasse, certificat) ou « http-<code> »."""


@dataclass(frozen=True)
class StoredDeclaration:
    declaration: Declaration
    declared_at: datetime


class DeclarationSender(Protocol):
    def send(self, payload: dict[str, object]) -> SendOutcome:
        """POST HTTPS vers la reception. Ne leve jamais : un echec est un SendOutcome."""
        ...


class DeclarationStore(Protocol):
    def load(self) -> StoredDeclaration | None: ...

    def save(self, stored: StoredDeclaration) -> None: ...

    def delete(self) -> None:
        """Efface la declaration (retrait). Jamais d'erreur si absente."""
        ...


class ReleaseSource(Protocol):
    def fetch_sha_list(self) -> str | None:
        """Contenu de download/sha.txt du site ; None si injoignable ou illisible. Ne leve jamais."""
        ...


@dataclass(frozen=True)
class ContactSupportServices:
    """Ce dont les ecrans et la ligne de commande ont besoin, pour UN logiciel (assemble par
    `omega_lib.infrastructure.declaration.build_contact_support`, ou de faux adaptateurs en test)."""

    software: str
    version: str
    store: DeclarationStore
    sender: DeclarationSender
    release_source: ReleaseSource
    open_url: Callable[[str], bool]
    """False sans session graphique : l'ecran affiche alors l'adresse."""
