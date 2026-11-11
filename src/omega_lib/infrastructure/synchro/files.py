# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Lecture tolerante et ecriture atomique des fichiers de contrat (spec etape 2, §2.6, §2.8)."""
from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, TypeVar

from omega_lib.synchro.constants import ZONE_DIR_DEFAULT, ZONE_DIR_ENV
from omega_lib.synchro.models import ReadResult, ReadStatus

T = TypeVar("T")

MAX_CONTRACT_BYTES = 1024 * 1024
"""Un jeton ou une fiche ne depasse jamais quelques ko : au-dela, le fichier est refuse."""


def zone_dir(environ: Mapping[str, str] | None = None) -> Path:
    """Zone neutre ; `OMEGA_SYNCHRO_DIR` la remplace (tests : jamais le vrai /var/lib)."""
    env = os.environ if environ is None else environ
    return Path(env.get(ZONE_DIR_ENV) or ZONE_DIR_DEFAULT)


def read_json(path: Path) -> ReadResult[Any]:
    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_CONTRACT_BYTES + 1)
    except FileNotFoundError:
        return ReadResult(ReadStatus.ABSENT, detail="file not found")
    except NotADirectoryError:
        return ReadResult(ReadStatus.ABSENT, detail="parent is not a directory")
    except OSError as error:
        return ReadResult(ReadStatus.UNREADABLE, detail=error.strerror or type(error).__name__)
    if len(raw) > MAX_CONTRACT_BYTES:
        return ReadResult(ReadStatus.INVALID, detail="file too large")
    try:
        return ReadResult(ReadStatus.OK, json.loads(raw.decode("utf-8")))
    except (UnicodeDecodeError, ValueError):
        return ReadResult(ReadStatus.INVALID, detail="not valid UTF-8 JSON")


def read_contract(path: Path, parse: Callable[[object], ReadResult[T]]) -> ReadResult[T]:
    raw = read_json(path)
    if not raw.ok:
        return ReadResult(raw.status, detail=raw.detail)
    return parse(raw.value)


def dumps(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def write_json_atomic(path: Path, payload: Mapping[str, Any], mode: int) -> None:
    """Fichier temporaire dans le meme dossier, fsync, chmod explicite, puis rename."""
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(dumps(payload))
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
