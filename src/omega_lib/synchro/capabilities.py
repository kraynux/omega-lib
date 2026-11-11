# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Capacites connues par outil (spec etape 2, §5). Un nom inconnu est tolere et affiche tel quel."""
from __future__ import annotations

KNOWN_CAPABILITIES: dict[str, tuple[str, ...]] = {
    "omega-serv": ("waf", "omega-waf", "magnet", "riposte", "active-defense", "native-engine", "blocklist"),
    "omega-fire": ("fail2ban", "nftables", "iptables", "log-library"),
    "omega-jail": ("jails", "bridge"),
    "omega-stress": ("distributed-worker", "native-generator"),
}

CONTRACTS: dict[str, str] = {
    "omega-jeton": "jeton d'installation (var/omega-jeton.json)",
    "omega-fiche": "fiche d'instance (sortie de `<outil> synchro fiche --format json`)",
    "omega-ban": "evenement du journal des bans (zone/bans/journal.jsonl)",
    "omega-bans-actifs": "etat des bans actifs (zone/bans/actifs.json)",
    "blocklist": "omega-serv blocklist list --format json",
    "waf-log": "journal des alertes du WAF d'omega-serv (lu par les jails)",
    "riposte-decisions": "decisions RIPOSTE d'omega-serv (lues par les jails RIPOSTE)",
}
"""Contrats nommes dans les jetons (`contracts`) et les fiches (`files.*.contract`)."""
