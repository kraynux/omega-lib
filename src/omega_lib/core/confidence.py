# Copyright (c) 2026 kraynux - Licence MIT
"""Modele de confiance commun a tous les outils omega-*.

Voir ~/DEV/SUITE/DECISIONS_ARCHITECTURE.md D-001 pour le rationnel complet.
Remplace l'ancien ordinal garanti/fiable/modere/incertain/cache, qui
confondait "a quel point on y croit" et "pourquoi on y croit".
"""
from __future__ import annotations

from enum import Enum


class ConfidenceLevel(str, Enum):
    """Nature de la preuve derriere une information, pas juste son degre.

    VERIFIED : fait protocolaire observe directement, non falsifiable par
        la cible (ex: RST TCP recu, succes/echec reel d'un handshake TLS).
    DECLARED : valeur auto-annoncee par la cible dans un champ qu'elle
        controle entierement (ex: header Server, banner SSH) — plausible
        mais falsifiable a volonte par la cible.
    CORROBORATED : une valeur DECLARED confirmee par au moins un indice
        comportemental independant.
    INFERRED : aucune declaration explicite ; deduit d'un pattern ou d'une
        heuristique.
    UNKNOWN : aucun indice exploitable, ou activement masque par la cible.
    """

    VERIFIED = "verified"
    DECLARED = "declared"
    CORROBORATED = "corroborated"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


_STRENGTH: dict[ConfidenceLevel, int] = {
    ConfidenceLevel.VERIFIED: 4,
    ConfidenceLevel.CORROBORATED: 3,
    ConfidenceLevel.DECLARED: 2,
    ConfidenceLevel.INFERRED: 1,
    ConfidenceLevel.UNKNOWN: 0,
}


def confidence_strength(level: ConfidenceLevel) -> int:
    """Force relative pour tri/affichage : VERIFIED > CORROBORATED >
    DECLARED > INFERRED > UNKNOWN. Pas un ordre implicite du type Python,
    d'ou cette fonction explicite plutot qu'un IntEnum."""
    return _STRENGTH[level]
