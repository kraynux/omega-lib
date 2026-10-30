# Copyright (c) 2026 kraynux - Licence MIT
"""Etat de traduction d'un outil (une instance par outil, un domaine gettext chacun).

La langue ne change jamais en cours de processus : on la choisit, l'interface redemarre
(plan i18n D6, os.execv), le nouveau processus installe la nouvelle langue AVANT de
construire son interface. Aucune I/O ici : les catalogues arrivent deja charges."""
from __future__ import annotations

import gettext

from omega_lib.i18n.models import Language
from omega_lib.i18n.policies import SOURCE_LANGUAGE_CODE, language_for

PSEUDO_OPEN = "⟦"
PSEUDO_CLOSE = "⟧"


class PseudoTranslations(gettext.NullTranslations):
    """Langue de controle : la phrase source entouree de ⟦ ⟧ (variables {x} intactes, donc
    .format() fonctionne toujours)."""

    def gettext(self, message: str) -> str:
        return f"{PSEUDO_OPEN}{message}{PSEUDO_CLOSE}"

    def ngettext(self, msgid1: str, msgid2: str, n: int) -> str:
        return self.gettext(msgid1 if n == 1 else msgid2)

    def pgettext(self, context: str, message: str) -> str:
        return self.gettext(message)

    def npgettext(self, context: str, msgid1: str, msgid2: str, n: int) -> str:
        return self.ngettext(msgid1, msgid2, n)


class TranslationState:
    """Langue active d'un outil. Par defaut : langue source, texte rendu tel quel."""

    def __init__(self) -> None:
        self._translations: gettext.NullTranslations = gettext.NullTranslations()
        self._language: Language = language_for(SOURCE_LANGUAGE_CODE)
        self._fell_back_from: str | None = None

    @property
    def language(self) -> Language:
        return self._language

    @property
    def fell_back_from(self) -> str | None:
        """Langue demandee mais indisponible au demarrage (message a afficher une fois)."""
        return self._fell_back_from

    def install(self, language: Language, translations: gettext.NullTranslations | None,
                fell_back_from: str | None = None) -> None:
        self._language = language
        self._translations = translations if translations is not None else gettext.NullTranslations()
        self._fell_back_from = fell_back_from

    def reset(self) -> None:
        self.install(language_for(SOURCE_LANGUAGE_CODE), None)

    def gettext(self, message: str) -> str:
        return self._translations.gettext(message)

    def ngettext(self, singular: str, plural: str, n: int) -> str:
        return self._translations.ngettext(singular, plural, n)


def mark(message: str) -> str:
    """N_() : marque une phrase pour l'extraction SANS la traduire (constantes definies au
    chargement d'un module, traduites plus tard a l'affichage)."""
    return message
