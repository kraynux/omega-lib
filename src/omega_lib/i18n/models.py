# Copyright (c) 2026 kraynux - Licence MIT
"""Entites de la langue d'interface."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LanguageStatus(Enum):
    """Statut affiche dans le selecteur (plan i18n D12) : une langue reste "en test"
    tant que l'utilisateur ne l'a pas validee a sa porte de validation."""

    SOURCE = "source"
    VALIDATED = "validated"
    TESTING = "testing"


@dataclass(frozen=True, slots=True)
class Language:
    code: str
    native_name: str
    status: LanguageStatus


@dataclass(frozen=True, slots=True)
class LanguageChoice:
    """Langue retenue au demarrage. `fell_back_from` : langue demandee mais indisponible
    (catalogue absent ou illisible) - l'interface repart alors en langue source."""

    language: Language
    fell_back_from: str | None = None
