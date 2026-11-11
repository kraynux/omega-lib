# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Constantes des contrats d'interconnexion (spec etape 2, §2, §3, §6, §7)."""
from __future__ import annotations

# Zone neutre (Q4, Q5 validees le 2026-11-10) : seul root y ecrit, le groupe lit.
ZONE_DIR_DEFAULT = "/var/lib/omega-synchro"
ZONE_DIR_ENV = "OMEGA_SYNCHRO_DIR"
"""Variable de test : les tests ne doivent jamais ecrire dans le vrai /var/lib."""
ZONE_GROUP = "omega-synchro"
ZONE_DIR_MODE = 0o2750
ZONE_FILE_MODE = 0o640

ZONE_REGISTRY = "registre.json"
ZONE_TOKENS_DIR = "jetons"
ZONE_SHEETS_DIR = "fiches"
ZONE_LINKS_DIR = "liens"
ZONE_BANS_DIR = "bans"
BAN_JOURNAL = "journal.jsonl"
ACTIVE_BANS = "actifs.json"
BAN_JOURNAL_MAX_BYTES = 10 * 1024 * 1024
"""Au-dela, journal.jsonl devient journal.jsonl.1 (un seul ancien garde)."""

# Jeton d'installation (Q1) : sous var/, exclu des archives, survit aux mises a jour.
TOKEN_RELATIVE_PATH = "var/omega-jeton.json"
TOKEN_FILE_MODE = 0o644

FORMAT_TOKEN = "omega-jeton"
FORMAT_SHEET = "omega-fiche"
FORMAT_BAN = "omega-ban"
FORMAT_ACTIVE_BANS = "omega-bans-actifs"
FORMAT_REGISTRY = "omega-registre"
FORMAT_LINK = "omega-lien"

SCHEMA_VERSIONS: dict[str, int] = {
    FORMAT_TOKEN: 1,
    FORMAT_SHEET: 1,
    FORMAT_BAN: 1,
    FORMAT_ACTIVE_BANS: 1,
    # Contenu fixe a l'etape 3 avec omega-connect, leur seul ecrivain.
    FORMAT_REGISTRY: 1,
    FORMAT_LINK: 1,
}
"""Version que CE code sait lire et ecrire. Ajout d'un champ facultatif : meme version ; retrait,
renommage, changement de sens ou de type : version + 1."""

TOOL_LAUNCHERS: dict[str, str] = {
    "omega-serv": "omega-serv.sh",
    "omega-fire": "omega-fire.sh",
    "omega-jail": "omega-jail.sh",
}
"""Lanceur de chaque outil, relatif a sa racine. Jamais lu dans un jeton (modifiable par
l'utilisateur) : omega-connect le deduit d'ici, le verifie, et le lance sous le compte proprietaire."""

MACHINE_ID_PATHS = ("/etc/machine-id", "/var/lib/dbus/machine-id")
