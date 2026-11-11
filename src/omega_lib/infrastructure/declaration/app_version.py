# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Version d'un outil, envoyee dans une declaration et comparee a la liste publiee : pyproject.toml
(seule source de la version, livre dans l'archive), repli sur les metadonnees du paquet installe
(outil charge par omega-suite) - meme regle qu'omega-serv / omega-log."""
from __future__ import annotations

import importlib.metadata
import re
from pathlib import Path

_VERSION_LINE = re.compile(r'^version = "([^"]+)"$', re.MULTILINE)


def project_version(project_root: Path, distribution: str) -> str:
    try:
        match = _VERSION_LINE.search((project_root / "pyproject.toml").read_text(encoding="utf-8"))
    except OSError:
        match = None
    if match:
        return match.group(1)
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0"
