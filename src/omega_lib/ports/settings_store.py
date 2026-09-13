# Copyright (c) 2026 kraynux - Licence MIT
"""Contrat de lecture/ecriture des preferences globales (settings.json).
Porte depuis omega-scan/omega-stress dans omega-lib (D-008)."""
from __future__ import annotations

from typing import Protocol


class SettingsStore(Protocol):
    """Implemente par chaque outil (ex.
    omega_check.infrastructure.storage.files.json_settings_store)."""

    def get(self, key: str, default: str | None = None) -> str | None: ...

    def set(self, key: str, value: str) -> None: ...

    def all(self) -> dict[str, str]: ...
