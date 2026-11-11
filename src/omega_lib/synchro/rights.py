# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Droits attendus par fichier partage (spec etape 2, §7.3) : ce qu'omega-connect verifiera, et ce
que les tests des outils controlent. Donnees seulement.

Marques dans les chemins : `<zone>` (zone neutre), `<racine>` (racine de l'outil),
`<omega-serv>` (racine d'une instance omega-serv). `owner` / `group` : un nom de compte, ou
`<proprietaire>` (proprietaire du dossier de l'outil)."""
from __future__ import annotations

from dataclasses import dataclass

from omega_lib.synchro.constants import (
    TOKEN_FILE_MODE,
    ZONE_DIR_MODE,
    ZONE_FILE_MODE,
    ZONE_GROUP,
)


@dataclass(frozen=True)
class ExpectedRight:
    key: str
    path: str
    owner: str
    group: str
    mode: int
    writers: tuple[str, ...]
    readers: tuple[str, ...]
    minimum: bool = False
    """Vrai : `mode` est un minimum (droits plus larges toleres) ; faux : valeur exacte."""
    must_exist: bool = False
    """Vrai : absent = lien casse (ex. journal d'un jail : fail2ban refuse de demarrer)."""


EXPECTED_RIGHTS: tuple[ExpectedRight, ...] = (
    ExpectedRight("zone-dirs", "<zone>/ (et sous-dossiers)", "root", ZONE_GROUP, ZONE_DIR_MODE,
                  ("omega-connect",), ("omega-serv (service)", "utilisateur")),
    ExpectedRight("zone-registry", "<zone>/registre.json, <zone>/liens/*.json", "root", ZONE_GROUP,
                  ZONE_FILE_MODE, ("omega-connect",), ("outils", "utilisateur")),
    ExpectedRight("zone-tokens", "<zone>/jetons/*.json", "root", ZONE_GROUP, ZONE_FILE_MODE,
                  ("omega-connect",), ("utilisateur",)),
    ExpectedRight("zone-sheets", "<zone>/fiches/*.json", "root", ZONE_GROUP, ZONE_FILE_MODE,
                  ("omega-connect",), ("outils", "utilisateur")),
    ExpectedRight("zone-bans", "<zone>/bans/journal.jsonl, <zone>/bans/actifs.json", "root", ZONE_GROUP,
                  ZONE_FILE_MODE, ("action fail2ban", "omega-fire"),
                  ("Active Defense (service)", "omega-fire", "utilisateur")),
    ExpectedRight("install-token", "<racine>/var/omega-jeton.json", "<proprietaire>", "", TOKEN_FILE_MODE,
                  ("l'outil",), ("omega-connect",)),
    ExpectedRight("serv-blocklist", "<omega-serv>/var/lib/waf/blocklist.json", "<proprietaire>", "omega-serv",
                  0o660, ("omega-serv (CLI et service)",), ("pont omega-jail", "omega-fire (par la CLI)"),
                  minimum=True),
    ExpectedRight("serv-jail-logs", "<omega-serv>/var/log/*.log, *.jsonl lus par un jail", "<proprietaire>",
                  "omega-serv", 0o660, ("omega-serv", "omega-waf"), ("fail2ban",), minimum=True, must_exist=True),
    ExpectedRight("jail-bridge", "/usr/local/lib/omega-jail/omega-jail-tailscale-bridge.py", "root", "root",
                  0o755, ("omega-jail (installation)",), ("fail2ban",)),
    ExpectedRight("fail2ban-omega-files", "/etc/fail2ban/{jail,filter,action}.d/omega-*", "root", "root",
                  0o644, ("omega-jail (installation)",), ("fail2ban", "omega-fire")),
)


def expected_right(key: str) -> ExpectedRight:
    return next(item for item in EXPECTED_RIGHTS if item.key == key)


def mode_matches(actual: int, right: ExpectedRight) -> bool:
    """Compare les 12 bits de droits (setgid compris) : exact, ou au moins `right.mode` si `minimum`."""
    actual &= 0o7777
    if right.minimum:
        return actual & right.mode == right.mode
    return actual == right.mode
