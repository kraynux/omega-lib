# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Lecture du journal des bans et de l'etat des bans actifs (spec etape 2, §6). Format fixe a l'etape 2,
ecrivains (action fail2ban, omega-fire) livres en phase 3.

Le lecteur lit d'abord `actifs.json`, puis suit `journal.jsonl` depuis sa position (inode + decalage) ;
une rotation ratee (inode change ou fichier plus court) le fait repartir de l'etat initial."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from omega_lib.infrastructure.synchro.files import read_contract
from omega_lib.synchro.codec import active_bans_from_dict, ban_event_from_dict
from omega_lib.synchro.models import ActiveBans, BanEvent, ReadResult, ReadStatus

MAX_LINE_BYTES = 8192


@dataclass(frozen=True)
class JournalPosition:
    inode: int = 0
    offset: int = 0


@dataclass(frozen=True)
class JournalRead:
    status: ReadStatus
    events: tuple[BanEvent, ...] = ()
    position: JournalPosition = JournalPosition()
    invalid_lines: int = 0
    incompatible_lines: int = 0
    restarted: bool = False
    """Vrai si la position ne correspondait plus (rotation) : relire l'etat initial."""


def read_active_bans(path: Path) -> ReadResult[ActiveBans]:
    return read_contract(path, active_bans_from_dict)


def read_ban_journal(path: Path, position: JournalPosition | None = None) -> JournalRead:
    start = position or JournalPosition()
    try:
        handle = path.open("rb")
    except FileNotFoundError:
        return JournalRead(ReadStatus.ABSENT, position=start)
    except OSError:
        return JournalRead(ReadStatus.UNREADABLE, position=start)
    with handle:
        info = os.fstat(handle.fileno())
        restarted = bool(start.inode) and (info.st_ino != start.inode or info.st_size < start.offset)
        offset = 0 if restarted or start.inode != info.st_ino else start.offset
        handle.seek(offset)
        events: list[BanEvent] = []
        invalid = incompatible = 0
        while True:
            line = handle.readline(MAX_LINE_BYTES + 1)
            if not line:
                break
            if not line.endswith(b"\n"):
                if len(line) <= MAX_LINE_BYTES:
                    break  # ligne en cours d'ecriture : relue au prochain passage
                invalid += 1
                handle.readline()  # reste de la ligne trop longue
                offset = handle.tell()
                continue
            offset += len(line)
            if not line.strip():
                continue
            try:
                result = ban_event_from_dict(json.loads(line.decode("utf-8")))
            except (UnicodeDecodeError, ValueError):
                invalid += 1
                continue
            if result.ok and result.value is not None:
                events.append(result.value)
            elif result.status is ReadStatus.INCOMPATIBLE:
                incompatible += 1
            else:
                invalid += 1
    return JournalRead(ReadStatus.OK, tuple(events), JournalPosition(info.st_ino, offset), invalid, incompatible,
                       restarted)
