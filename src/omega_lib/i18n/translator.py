# Copyright (c) 2026 kraynux - Licence MIT
"""Traducteur d'un outil omega (OMEGA-SUITE_PLAN-DETAILLE_I18N.md §5) - pur, sans I/O.

Chaque outil en a UN, dans son `shared/i18n.py`, qui en expose `_`, `N_`, `ngettext`,
`lazy`, `retranslate`, `translating_as` (meme interface que omega_fire/shared/i18n.py).
Les catalogues arrivent deja charges (omega_lib.infrastructure.i18n) : le catalogue propre
de l'outil, chaine au catalogue partage `omega-lib` (gettext add_fallback, Q3).

Langue des exports (lot N) : `translating_as(etat)` fait repondre `_()` dans une autre
langue pour le seul fil d'execution (ou la seule tache asyncio) qui produit l'export."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from omega_lib.i18n.policies import PSEUDO_LANGUAGE_CODE, text_direction
from omega_lib.i18n.service import TranslationState


class ToolTranslator:
    def __init__(self, domain: str) -> None:
        self.domain = domain
        """Nom des catalogues de l'outil : locale/<langue>/LC_MESSAGES/<domain>.mo."""
        self.state = TranslationState()
        self._export_state: ContextVar[TranslationState | None] = ContextVar(
            f"{domain}_export_language", default=None
        )

    def active_state(self) -> TranslationState:
        """Langue des exports pendant un export qui en a une autre, sinon celle de l'interface."""
        return self._export_state.get() or self.state

    @contextmanager
    def translating_as(self, state: TranslationState | None) -> Iterator[None]:
        """Traduit dans `state` le temps du bloc (None : langue de l'interface, rien ne change)."""
        token = self._export_state.set(state)
        try:
            yield
        finally:
            self._export_state.reset(token)

    def gettext(self, message: str) -> str:
        return self.active_state().gettext(message)

    def ngettext(self, singular: str, plural: str, n: int) -> str:
        return self.active_state().ngettext(singular, plural, n)

    def lazy(self, msgid: str, **params: object) -> str:
        """`lazy(N_("Port {port} ouvert"), port=22)` : comme `_(...).format(...)`, mais le
        texte garde sa source pour etre recompose dans une autre langue (retranslate)."""
        return LazyText(self, msgid, params)

    def log_text(self, msgid: str, **params: object) -> str:
        """Ligne de journal relayee a l'ecran (plan i18n R2) : le fichier journal la garde EN
        FRANCAIS (texte source compose), l'ecran de progression la retraduit (log_message)."""
        return LogText(msgid, params)

    def log_message(self, msg: object, args: object = None) -> str:
        """Texte affiche pour une ligne de journal relayee (record.msg, record.args) : traduite
        dans la langue active, arguments `%` appliques ensuite. Traduction illisible : la
        ligne francaise d'origine, jamais d'erreur."""
        if isinstance(msg, RecomposableText):
            text = str(self.retranslate(msg))
        elif isinstance(msg, str):
            text = self.gettext(msg)
        else:
            text = str(msg)
        if not args:
            return text
        try:
            return text % args
        except (TypeError, ValueError, KeyError):
            return str(msg) % args

    def retranslate(self, value: object) -> object:
        """Recompose un LazyText dans la langue active ; toute autre valeur rendue telle quelle."""
        if isinstance(value, RecomposableText):
            params = {key: self.retranslate(param) for key, param in value.params.items()}
            text = self.gettext(value.msgid)
            return text.format(**params) if params else text
        return value

    def html_lang(self) -> str:
        """Attribut lang= des exports HTML (BCP 47 : zh_CN -> zh-CN ; langue de controle = fr)."""
        code = self.active_state().language.code
        return "fr" if code == PSEUDO_LANGUAGE_CODE else code.replace("_", "-")

    def html_dir(self) -> str:
        """Attribut dir= des exports HTML : "rtl" en arabe, "ltr" sinon."""
        return text_direction(self.active_state().language.code)


class RecomposableText(str):
    """Texte qui garde sa source (msgid) et ses valeurs pour etre recompose dans une autre
    langue (retranslate)."""

    msgid: str
    params: dict[str, object]


class LazyText(RecomposableText):
    """Texte traduit a sa creation (langue active)."""

    def __new__(cls, translator: ToolTranslator, msgid: str, params: dict[str, object]) -> LazyText:  # noqa: PYI034
        text = translator.gettext(msgid)
        obj = super().__new__(cls, text.format(**params) if params else text)
        obj.msgid = msgid
        obj.params = params
        return obj


class LogText(RecomposableText):
    """Texte compose EN FRANCAIS (langue source) : ce qu'ecrit le fichier journal."""

    def __new__(cls, msgid: str, params: dict[str, object]) -> LogText:  # noqa: PYI034
        obj = super().__new__(cls, msgid.format(**params) if params else msgid)
        obj.msgid = msgid
        obj.params = params
        return obj
