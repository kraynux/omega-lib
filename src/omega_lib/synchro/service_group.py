# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Groupe de la zone donne au service systemd d'un outil (spec etape 3, §5, lot E ; decision de l'auteur du
2026-11-10 : complement systemd plutot que reecriture de l'unite).

L'outil (omega-serv) ecrit lui-meme `/etc/systemd/system/<service>.service.d/omega-synchro.conf`, qui ne contient
que `SupplementaryGroups=omega-synchro` : son unite n'est jamais touchee, et le retrait est exact. omega-connect
le lui demande et le verifie ; il ne l'ecrit jamais. Le complement doit disparaitre avant le groupe : un service
dont le groupe secondaire n'existe plus ne demarre plus (systemd, code 216/GROUP)."""
from __future__ import annotations

from omega_lib.synchro.constants import ZONE_GROUP

SYSTEMD_UNIT_DIR = "/etc/systemd/system"
DROP_IN_NAME = "omega-synchro.conf"
DROP_IN_MODE = 0o644


def drop_in_directory(service: str, unit_dir: str = SYSTEMD_UNIT_DIR) -> str:
    return f"{unit_dir.rstrip('/')}/{_unit_name(service)}.d"


def drop_in_path(service: str, unit_dir: str = SYSTEMD_UNIT_DIR) -> str:
    return f"{drop_in_directory(service, unit_dir)}/{DROP_IN_NAME}"


def drop_in_text() -> str:
    return ("# Ecrit par omega-serv a la demande d'omega-connect : le service lit la zone neutre.\n"
            "# Retrait : omega-serv synchro groupe-service retirer (jamais a la main avant omega-connect retirer).\n"
            "[Service]\n"
            f"SupplementaryGroups={ZONE_GROUP}\n")


def grants_zone_group(text: str) -> bool:
    """Le complement donne bien le groupe de la zone (section [Service], ligne SupplementaryGroups=)."""
    section = ""
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line
        elif section == "[Service]" and line.startswith("SupplementaryGroups=") and \
                ZONE_GROUP in line.removeprefix("SupplementaryGroups=").split():
            return True
    return False


def service_name(unit: str) -> str:
    """`omega-serv.service` -> `omega-serv`."""
    return unit.removesuffix(".service")


def _unit_name(service: str) -> str:
    return service if service.endswith(".service") else f"{service}.service"
