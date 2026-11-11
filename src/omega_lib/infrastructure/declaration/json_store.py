# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Stockage de la declaration anonyme : `var/declaration.json` de l'outil (repris d'omega-log, un
seul ecrivain : l'utilisateur). Ecriture atomique (fichier temporaire puis rename), fichier en 0600."""
from __future__ import annotations

import contextlib
import json
import os
from datetime import datetime
from pathlib import Path

from omega_lib.declaration.models import Declaration
from omega_lib.ports.declaration import StoredDeclaration


class JsonDeclarationStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> StoredDeclaration | None:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(data, dict) or not isinstance(data.get("cle"), str):
            return None
        try:
            declared_at = datetime.fromisoformat(str(data.get("declare_le") or ""))
        except ValueError:
            return None
        declaration = Declaration(data["cle"], str(data.get("continent") or ""), str(data.get("pays") or ""))
        return StoredDeclaration(declaration, declared_at)

    def save(self, stored: StoredDeclaration) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        declaration = stored.declaration
        payload = {"cle": declaration.key, "continent": declaration.continent, "pays": declaration.country,
                   "declare_le": stored.declared_at.isoformat()}
        tmp = self._path.with_name(f".{self._path.name}.{os.getpid()}.tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
            os.replace(tmp, self._path)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise

    def delete(self) -> None:
        with contextlib.suppress(OSError):
            self._path.unlink(missing_ok=True)
