# Copyright (c) 2026 kraynux - Licence MIT
"""Alias de type transverses reutilises dans les signatures de commands/queries.

Porte verbatim depuis omega_scan.shared.typing.
"""
from __future__ import annotations

from collections.abc import Callable

IdFactory = Callable[[], str]
"""Signature d'un generateur d'identifiant injecte dans un command de
creation (voir shared/ids.py::new_id, l'implementation de production)."""
