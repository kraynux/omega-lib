# Copyright (c) 2026 kraynux - Licence MIT
"""Politique de choix de la langue - pur, sans I/O."""
from __future__ import annotations

from collections.abc import Iterable, Mapping

from omega_lib.i18n.models import Language, LanguageChoice, LanguageStatus

SOURCE_LANGUAGE_CODE = "fr"
"""Langue des textes ecrits dans le code (plan i18n D2) : toujours disponible, ne depend
d'aucun fichier, ne peut donc jamais etre cassee par une traduction."""

PSEUDO_LANGUAGE_CODE = "x-test"
"""Langue de controle (plan i18n §4.7) : chaque phrase traduisible entouree de ⟦ ⟧, pour
reperer a l'oeil une phrase restee en dur. Jamais un fichier : generee a la volee."""

NATIVE_NAMES: Mapping[str, str] = {
    "fr": "Français",
    "en": "English",
    "es": "Español",
    "de": "Deutsch",
    "it": "Italiano",
    "pt_BR": "Português (Brasil)",
    "nl": "Nederlands",
    "pl": "Polski",
    "ru": "Русский",
    "zh_CN": "简体中文",
    "vi": "Tiếng Việt",
    "th": "ไทย",
    "id": "Bahasa Indonesia",
    "ja": "日本語",
    "ko": "한국어",
    "hi": "हिन्दी",
    "ar": "العربية",
    PSEUDO_LANGUAGE_CODE: "Test ⟦…⟧ (développement)",
}
"""Chaque langue s'affiche dans SA langue : un utilisateur perdu dans une interface qu'il ne
lit pas retrouve toujours la sienne."""

PREFERRED_ORDER: tuple[str, ...] = (
    "fr", "en", "es", "pt_BR", "it", "de", "nl", "pl", "ru",
    "zh_CN", "vi", "th", "id", "ja", "ko", "hi", "ar",
)
"""Liste et ordre DEFINITIFS (decision utilisateur 2026-10-23, liste corrigee) : 17 langues."""

CONSOLE_FALLBACK_LANGUAGE_CODE = "en"
"""Langue de repli quand le terminal ne sait pas afficher l'ecriture de la langue choisie
(decision utilisateur 2026-10-22 : anglais, lisible par le plus grand nombre)."""

LATIN_CONSOLE_FAMILIES: frozenset[str] = frozenset({"linux-tty"})
"""Familles de terminal (terminal/policies.py) limitees a une police console : ni chinois, ni
devanagari, ni arabe affichables (police de 512 glyphes au plus)."""

WIDE_SCRIPT_LANGUAGES: frozenset[str] = frozenset({"vi", "zh_CN", "th", "ja", "ko", "hi", "ar"})
"""Langues dont l'ecriture est absente des polices console. Vietnamien ajoute (decision
utilisateur 2026-10-23) : la seule police console qui a ses lettres (viscii10-8x16) n'a aucun
caractere de cadre, et aucune police n'a les deux."""

RIGHT_TO_LEFT_LANGUAGES: frozenset[str] = frozenset({"ar"})
"""Langues ecrites de droite a gauche : `dir="rtl"` dans les pages HTML."""


def text_direction(code: str) -> str:
    """Valeur de l'attribut HTML `dir` : "rtl" pour l'arabe, "ltr" sinon."""
    return "rtl" if code in RIGHT_TO_LEFT_LANGUAGES else "ltr"


def console_fallback_language(code: str, terminal_family: str | None) -> str | None:
    """Langue a utiliser A LA PLACE de `code` pour cette session, ou None si `code` s'affiche.
    Le reglage choisi n'est jamais modifie : dans un vrai terminal graphique, la langue
    choisie revient d'elle-meme."""
    if code in WIDE_SCRIPT_LANGUAGES and terminal_family in LATIN_CONSOLE_FAMILIES:
        return CONSOLE_FALLBACK_LANGUAGE_CODE
    return None


def normalize_language_code(raw: str | None) -> str:
    """'EN' -> 'en', 'zh-cn' -> 'zh_CN', 'fr_FR.UTF-8' -> 'fr' si seul 'fr' est connu."""
    if not raw:
        return ""
    value = raw.strip().split(".")[0].replace("-", "_")
    if value.lower() == PSEUDO_LANGUAGE_CODE.replace("-", "_"):
        return PSEUDO_LANGUAGE_CODE
    for known in NATIVE_NAMES:
        if value.lower() == known.lower():
            return known
    base = value.split("_")[0].lower()
    return base if base in NATIVE_NAMES else value


def language_for(code: str, status: LanguageStatus = LanguageStatus.TESTING) -> Language:
    if code == SOURCE_LANGUAGE_CODE:
        return Language(code, NATIVE_NAMES[code], LanguageStatus.SOURCE)
    return Language(code, NATIVE_NAMES.get(code, code), status)


def ordered_languages(available: Mapping[str, LanguageStatus], *, include_pseudo: bool) -> list[Language]:
    """Langue source TOUJOURS en tete (plan i18n §5.3), puis l'ordre des lots
    (PREFERRED_ORDER), puis toute autre langue deposee, puis la langue de controle."""
    codes = [c for c in available if c not in (SOURCE_LANGUAGE_CODE, PSEUDO_LANGUAGE_CODE)]
    ordered = sorted(codes, key=lambda c: (PREFERRED_ORDER.index(c) if c in PREFERRED_ORDER else len(PREFERRED_ORDER), c))
    languages = [language_for(SOURCE_LANGUAGE_CODE)] + [language_for(c, available[c]) for c in ordered]
    if include_pseudo:
        languages.append(language_for(PSEUDO_LANGUAGE_CODE, LanguageStatus.TESTING))
    return languages


def resolve_language(
    requested: str | None,
    available: Iterable[str],
    statuses: Mapping[str, LanguageStatus] | None = None,
) -> LanguageChoice:
    """Langue demandee si elle est disponible, sinon langue source avec la trace du repli.
    Vide ou absent = langue source, sans repli signale (choix par defaut, pas une erreur)."""
    code = normalize_language_code(requested)
    if not code or code == SOURCE_LANGUAGE_CODE:
        return LanguageChoice(language_for(SOURCE_LANGUAGE_CODE))
    offered = set(available) | {PSEUDO_LANGUAGE_CODE}
    if code not in offered:
        return LanguageChoice(language_for(SOURCE_LANGUAGE_CODE), fell_back_from=code)
    status = (statuses or {}).get(code, LanguageStatus.TESTING)
    return LanguageChoice(language_for(code, status))
