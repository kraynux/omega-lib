"""Largeur des voyelles accrochees « espacantes » (hindi ; issu d'omega-serv, plan i18n lots 10-11 ; partage dans omega-lib pour toute la suite).

Rich/Textual comptent les marques combinantes espacantes (categorie Unicode Mc : voyelles
devanagari `ि`, `ी`, `ा`...) pour 0 colonne ; glibc et VTE (Terminator, GNOME Terminal) les
affichent sur 1 colonne. Mesure reelle le 2026-10-22 dans Terminator : `हिन्दी` = 3 colonnes
pour Rich, 5 a l'ecran - chaque ligne hindi decalait cadres et colonnes. On aligne donc la
table de largeurs de Rich sur glibc pour Mc, une seule fois au demarrage, avant tout rendu.

Aucun effet sur les langues deja livrees (fr/en/es/ru/zh_CN n'ont aucun caractere Mc). Table
interne de Rich : en cas de changement de Rich, on ne plante jamais - la correction est
simplement ignoree (le texte reste affiche, seul l'alignement hindi serait decale)."""
from __future__ import annotations

import unicodedata

_applied = False


def _widened(widths: list[tuple[int, int, int]]) -> list[tuple[int, int, int]]:
    """Chaque plage de largeur 0 est redecoupee : Mc -> 1, le reste inchange."""
    result: list[tuple[int, int, int]] = []

    def push(start: int, end: int, width: int) -> None:
        if result and result[-1][2] == width and result[-1][1] == start - 1:
            result[-1] = (result[-1][0], end, width)
        else:
            result.append((start, end, width))

    for start, end, width in widths:
        if width != 0:
            push(start, end, width)
            continue
        for codepoint in range(start, end + 1):
            spacing_mark = unicodedata.category(chr(codepoint)) == "Mc"
            push(codepoint, codepoint, 1 if spacing_mark else 0)
    return result


def align_spacing_marks_with_terminal() -> bool:
    """Applique la correction (idempotent). Retourne False si Rich n'a pas la structure
    attendue (correction ignoree, jamais d'erreur)."""
    global _applied
    if _applied:
        return True
    try:
        import importlib

        from rich import cells
        from rich._unicode_data import load

        for version in {load("auto").unicode_version, load("latest").unicode_version}:
            module = importlib.import_module(f"rich._unicode_data.unicode{version.replace('.', '-')}")
            table = module.cell_table
            module.cell_table = table._replace(widths=_widened(list(table.widths)))  # type: ignore[attr-defined]
        load.cache_clear()
        cells.get_character_cell_size.cache_clear()
        cells.cached_cell_len.cache_clear()
    except Exception:  # noqa: BLE001 - structure interne de Rich modifiee : on n'empeche jamais l'affichage
        return False
    _applied = True
    return True
