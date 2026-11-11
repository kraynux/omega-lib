# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Constantes et modeles de « Contact et support » (pur, aucune I/O).

Ce qu'une declaration envoie, et rien d'autre : une cle tiree au hasard (sans lien avec la
machine), le logiciel (la reception tient une liste fermee), sa version, le mode « unique » et,
facultatifs, un continent et un pays pris dans des listes fermees."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

SITE_URL = "https://kraynux.snake-mackarel.ts.net/"
RECEPTION_URL = SITE_URL + "compteur/"
"""Reception des declarations (hpc-109), la meme pour tous les logiciels omega."""
PAYPAL_URL = "https://paypal.me/kraynux"
SUPPORT_MAIL = "kraynux@proton.me"
CONTACT_FORM_URL = SITE_URL + "contact/"

SOFTWARES = (
    "omega-serv", "omega-log", "omega-fire", "omega-jail", "omega-suite", "omega-scan", "omega-check",
    "omega-deep", "omega-fold", "omega-stress", "omega-track", "omega-fuzz", "omega-connect",
)
"""Liste fermee de la reception (index.php, SOFTWARES) : un autre nom y donne 400."""

MODE_ONCE = "unique"
"""Seul mode des outils sans service (omega-serv propose aussi « quotidien », envoye par `serve`)."""

OTHER = "autre"
CONTINENTS = ("AF", "AN", "AS", "EU", "NA", "OC", "SA")


@dataclass(frozen=True)
class Declaration:
    key: str
    continent: str = ""
    country: str = ""


class UpdateStatus(Enum):
    UP_TO_DATE = "up_to_date"
    UPDATE_AVAILABLE = "update_available"
    AHEAD = "ahead"
    """Version installee plus recente que la derniere publiee (version en cours, pas encore publiee)."""
    UNKNOWN = "unknown"
    """Liste illisible, site injoignable ou version installee non reconnue."""


@dataclass(frozen=True)
class UpdateCheck:
    status: UpdateStatus
    installed: str
    latest: str = ""
    archive_url: str = ""
    notes_url: str = ""
