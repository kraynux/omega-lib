# Copyright (c) 2026 kraynux - Licence MIT
"""Langue de l'interface d'un outil omega (OMEGA-SUITE_PLAN-DETAILLE_I18N.md §5, lot 2) :
choix au demarrage, selecteur, langue des exports - repris d'omega_fire/application/commands/
select_language.py, ecrit une seule fois ici pour les 7 outils et la suite.

Ordre de priorite au demarrage :
  0. langue imposee par l'hote (omega-suite, Q2) - l'outil ne lit alors rien d'autre ;
  1. variable d'environnement OMEGA_<OUTIL>_LANG (une fois, sans toucher au reglage) - voie de
     secours : `OMEGA_FOLD_LANG=fr ./omega-fold.sh` relance en francais ;
  2. reglage `language` du fichier de reglages (Reglages -> "Langue / Language") ;
  3. francais.
Langue indisponible ou catalogue illisible : francais, et le repli est memorise pour etre
signale une fois a l'ecran. Jamais d'erreur au demarrage.

Console TTY Linux avec une langue a ecriture large : anglais pour CETTE session seulement,
le reglage n'est pas modifie (meme regle qu'omega-serv et omega-fire)."""
from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field
from pathlib import Path

from omega_lib.i18n.host import host_export_language, host_language
from omega_lib.i18n.models import Language, LanguageChoice, LanguageStatus
from omega_lib.i18n.policies import (
    PSEUDO_LANGUAGE_CODE,
    SOURCE_LANGUAGE_CODE,
    console_fallback_language,
    language_for,
    normalize_language_code,
    ordered_languages,
    resolve_language,
)
from omega_lib.i18n.service import TranslationState
from omega_lib.i18n.translator import ToolTranslator
from omega_lib.infrastructure.i18n.gettext_catalogs import (
    SHARED_LOCALE_DIR,
    CatalogError,
    discover_tool_catalogs,
    load_tool_translations,
)
from omega_lib.ports.settings_store import SettingsStore

LANGUAGE_LABEL = "Langue / Language"
"""Libelle du selecteur, JAMAIS traduit : reperable quelle que soit la langue affichee."""

LANGUAGE_KEY = "language"
EXPORT_LANGUAGE_KEY = "export_language"
"""Langue des exports (lot N, Q5) : vide = comme l'interface."""

OFFER_PSEUDO_LANGUAGE = False
"""Langue de controle ⟦…⟧ proposee dans les selecteurs pendant les lots de traduction ; a
passer a False a la publication finale (comme omega-serv 2.0.0 et omega-fire 3.5). Toujours
accessible ensuite par OMEGA_<OUTIL>_LANG=x-test."""


class UnknownLanguageError(ValueError):
    """Langue demandee absente des catalogues proposes."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass
class ToolLanguage:
    """Une instance par outil (dans son app/), autour du traducteur de son shared/i18n.py."""

    translator: ToolTranslator
    locale_dir: Path
    env_var: str
    """OMEGA_<OUTIL>_LANG"""
    shared_dir: Path = SHARED_LOCALE_DIR
    console_fallback_from: str | None = field(default=None, init=False)
    """Langue choisie mais remplacee par l'anglais faute de pouvoir l'afficher dans ce
    terminal (signalee une fois a l'ecran), sinon None."""

    @property
    def changed_env_var(self) -> str:
        """Pose juste avant os.execv() : le nouveau processus confirme la nouvelle langue."""
        return self.env_var.removesuffix("_LANG") + "_LANGUAGE_CHANGED"

    @property
    def state(self) -> TranslationState:
        return self.translator.state

    def statuses(self) -> dict[str, LanguageStatus]:
        return discover_tool_catalogs(self.locale_dir, self.translator.domain, self.shared_dir)

    def available(self) -> list[Language]:
        """Langues du selecteur : francais en tete, puis l'ordre des lots."""
        return ordered_languages(self.statuses(), include_pseudo=OFFER_PSEUDO_LANGUAGE)

    def install(self, *, settings_store: SettingsStore | None, environ: Mapping[str, str],
                terminal_family: str | None = None) -> LanguageChoice:
        imposed = host_language()
        statuses = self.statuses()
        offered = list(statuses) + [PSEUDO_LANGUAGE_CODE]
        self.console_fallback_from = None
        if imposed is not None:
            # La suite a deja applique le repli console : la langue recue est definitive.
            return self._install_choice(resolve_language(imposed, offered, statuses))
        stored = ""
        if settings_store is not None:
            try:
                stored = settings_store.get(LANGUAGE_KEY, "") or ""
            except (OSError, ValueError):
                stored = ""  # reglages illisibles : francais, jamais d'erreur au demarrage
        choice = resolve_language(environ.get(self.env_var) or stored, offered, statuses)
        replacement = console_fallback_language(choice.language.code, terminal_family)
        if replacement is not None and choice.fell_back_from is None:
            self.console_fallback_from = choice.language.code
            choice = resolve_language(replacement, offered, statuses)
        return self._install_choice(choice)

    def _install_choice(self, choice: LanguageChoice) -> LanguageChoice:
        state = self.translator.state
        if choice.fell_back_from is None and choice.language.code != SOURCE_LANGUAGE_CODE:
            try:
                translations = load_tool_translations(
                    self.locale_dir, self.translator.domain, choice.language.code, self.shared_dir)
            except CatalogError:
                choice = LanguageChoice(language_for(SOURCE_LANGUAGE_CODE),
                                        fell_back_from=choice.language.code)
            else:
                state.install(choice.language, translations)
                return choice
        state.install(choice.language, None, fell_back_from=choice.fell_back_from)
        return choice

    def select(self, settings_store: SettingsStore, language_code: str) -> Language:
        """Enregistre la langue choisie ; appliquee au redemarrage de l'interface."""
        code = normalize_language_code(language_code)
        offered = {language.code: language for language in self.available()}
        if code not in offered:
            raise UnknownLanguageError(language_code)
        settings_store.set(LANGUAGE_KEY, "" if code == SOURCE_LANGUAGE_CODE else code)
        return offered[code]

    def prepare_restart_environment(self, environ: MutableMapping[str, str], language_code: str) -> None:
        """Environnement du processus relance : confirmation de la langue demandee, et la
        surcharge OMEGA_<OUTIL>_LANG eventuelle retiree (elle masquerait le nouveau choix)."""
        environ[self.changed_env_var] = language_code
        environ.pop(self.env_var, None)

    def select_export_language(self, settings_store: SettingsStore, language_code: str) -> None:
        """"" = comme l'interface. Effet immediat : chaque export relit le reglage."""
        if not language_code:
            settings_store.set(EXPORT_LANGUAGE_KEY, "")
            return
        code = normalize_language_code(language_code)
        if code not in {language.code for language in self.available()}:
            raise UnknownLanguageError(language_code)
        settings_store.set(EXPORT_LANGUAGE_KEY, code)

    def export_language_setting(self, settings_store: SettingsStore | None) -> str:
        """Valeur du reglage « Langue des exports » ("" = comme l'interface) ; dans omega-suite,
        celle de la suite (un seul reglage pour tous les outils, Q5)."""
        hosted = host_export_language()
        if hosted is not None:
            raw = hosted
        elif settings_store is None:
            return ""
        else:
            try:
                raw = settings_store.get(EXPORT_LANGUAGE_KEY, "") or ""
            except OSError:
                return ""
        try:
            return normalize_language_code(raw) if raw else ""
        except ValueError:
            return ""

    def export_language_override(self, settings_store: SettingsStore | None) -> str | None:
        """Langue a utiliser pour un export, ou None s'il suit l'interface."""
        code = self.export_language_setting(settings_store)
        if not code or code == self.translator.state.language.code:
            return None
        return code

    def export_state(self, settings_store: SettingsStore | None) -> TranslationState | None:
        """Etat a passer a translating_as() autour d'un export : None = langue de l'interface
        (reglage vide, meme langue, ou catalogue absent - jamais d'erreur pour un export)."""
        code = self.export_language_override(settings_store)
        if code is None:
            return None
        try:
            return self.load_state(code)
        except CatalogError:
            return None

    def load_state(self, code: str) -> TranslationState:
        """Etat de traduction d'une autre langue (exports), a passer a translating_as().
        Leve CatalogError si aucun catalogue n'existe pour cette langue."""
        state = TranslationState()
        state.install(language_for(code), load_tool_translations(
            self.locale_dir, self.translator.domain, code, self.shared_dir))
        return state
