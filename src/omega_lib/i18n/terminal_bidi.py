"""Ordre d'affichage droite-a-gauche dans la TUI (arabe ; issu d'omega-serv, plan i18n lot 11, option C ; partage dans omega-lib pour toute la suite).

Mesure reelle le 2026-10-23 dans Terminator (VTE 0.84) : en mode « implicite » (defaut), le
terminal reordonne lui-meme toute la portion de ligne situee entre deux mots arabes - cadres,
fonds et bordures des boutons compris. Deux boutons voisins echangeaient leur place, les
bordures se retrouvaient au milieu, le fond debordait (capture utilisateur arabe.png).

Correction choisie par l'utilisateur (option C, test arabic2.png : aucun debordement) :
- le terminal passe en mode « explicite » (ECMA-48 BDSM, `CSI 8 l`) : il ne deplace plus rien
  et continue de lier les lettres ;
- le programme met lui-meme chaque morceau de texte dans l'ordre visuel, morceau par morceau
  (un libelle de bouton = un morceau) : rien ne sort jamais de sa case, la largeur ne change pas.

Les terminaux sans gestion bidi (Kitty, Alacritty, WezTerm...) ignorent `CSI 8 l` et recoivent
le meme texte deja ordonne : l'ordre y devient correct aussi.

Algorithme bidi Unicode (UAX #9) simplifie a une ligne sans incorporation explicite : direction
de base = premier caractere fort (P2/P3), regles W1-W7, N1-N2, I1-I2, L2 (inversion par niveau),
L4 (miroir des parentheses). Les marques combinantes restent accrochees a leur lettre. Les
espaces de bord du morceau (marges de centrage) ne bougent jamais. Un isolement (U+2066-U+2068
... U+2069, pose autour de {date} dans le catalogue arabe) est ordonne a part puis traite comme
un seul neutre ; ces controles et les marques LRM/RLM, larges de 0 colonne, ne sont jamais
ecrits. Ecart assume avec UAX #9 : une barre oblique collee a une lettre latine compte comme
latine, pour qu'un chemin (`/var/www/html`, `secure/waf/rules/`) reste d'un seul tenant."""
from __future__ import annotations

import re
import unicodedata

ENTER_EXPLICIT_MODE = "\x1b[8l"
LEAVE_EXPLICIT_MODE = "\x1b[8h"

_RTL_CHARACTER = re.compile("[\u0590-\u08ff\ufb1d-\ufdff\ufe70-\ufefc]")
_INVISIBLE_CONTROLS = dict.fromkeys(map(ord, "\u200e\u200f\u202a\u202b\u202c\u202d\u202e"))
_ISOLATE_OPENERS = {"\u2066": False, "\u2067": True, "\u2068": None}  # LRI, RLI, FSI (auto)
_ISOLATE_CLOSER = "\u2069"
_JOINER = "\u200d"
_MIRRORS = {"(": ")", ")": "(", "[": "]", "]": "[", "{": "}", "}": "{", "<": ">", ">": "<", "«": "»", "»": "«"}
_STRONG = {"L", "R"}
_NUMBERS = {"EN", "AN"}

_installed = False


def _clusters(text: str) -> tuple[list[str], set[int]]:
    """Lettre + marques combinantes qui la suivent (jamais separees par l'inversion). Un
    isolement devient une seule grappe, deja ordonnee ; leurs positions sont renvoyees a part."""
    clusters: list[str] = []
    isolates: set[int] = set()
    index = 0
    while index < len(text):
        char = text[index]
        if char in _ISOLATE_OPENERS:
            depth, end = 1, index + 1
            while end < len(text) and depth:
                depth += text[end] in _ISOLATE_OPENERS
                depth -= text[end] == _ISOLATE_CLOSER
                end += 1
            inner = text[index + 1 : end if depth else end - 1]
            isolates.add(len(clusters))
            clusters.append(_ordered(inner, _ISOLATE_OPENERS[char]))
            index = end
            continue
        if char == _ISOLATE_CLOSER:
            index += 1
            continue
        attaches = unicodedata.category(char) in ("Mn", "Me", "Mc") or char == _JOINER
        if clusters and attaches and len(clusters) - 1 not in isolates:
            clusters[-1] += char
        else:
            clusters.append(char)
        index += 1
    return clusters, isolates


def _raw_type(clusters: list[str], index: int, isolates: set[int]) -> str:
    if index in isolates or not clusters[index]:
        return "ON"
    kind = unicodedata.bidirectional(clusters[index][0]) or "ON"
    if clusters[index] == "/":
        neighbours = [clusters[i] for i in (index - 1, index + 1) if 0 <= i < len(clusters) and i not in isolates]
        if any(unicodedata.bidirectional(neighbour[0]) == "L" for neighbour in neighbours if neighbour):
            return "L"
    return "ON" if kind == "NSM" else kind


def _direction(kind: str) -> str | None:
    if kind == "L":
        return "L"
    if kind == "R" or kind in _NUMBERS:
        return "R"
    return None


def _resolved_types(clusters: list[str], isolates: set[int], base_rtl: bool) -> list[str]:
    sos = "R" if base_rtl else "L"
    # W1 : NSM deja accroche a sa lettre (grappes) ; W2-W3 : EN apres AL -> AN, AL -> R.
    last_strong = sos
    types: list[str] = []
    for index in range(len(clusters)):
        kind = _raw_type(clusters, index, isolates)
        if kind == "EN" and last_strong == "AL":
            kind = "AN"
        if kind in ("L", "R", "AL"):
            last_strong = kind
        types.append("R" if kind == "AL" else kind)
    # W4 : un separateur seul entre deux nombres du meme type les relie.
    for index in range(1, len(types) - 1):
        before, after = types[index - 1], types[index + 1]
        if types[index] == "ES" and before == after == "EN":
            types[index] = "EN"
        elif types[index] == "CS" and before == after and before in _NUMBERS:
            types[index] = before
    # W5 : ET colles a un EN deviennent EN.
    for index, kind in enumerate(types):
        if kind != "ET":
            continue
        left = index
        while left > 0 and types[left - 1] == "ET":
            left -= 1
        right = index
        while right < len(types) - 1 and types[right + 1] == "ET":
            right += 1
        if (left > 0 and types[left - 1] == "EN") or (right < len(types) - 1 and types[right + 1] == "EN"):
            types[index] = "EN"
    # W6 : separateurs restants -> neutres ; W7 : EN apres un L (ou un debut L) -> L.
    last_strong = sos
    for index, kind in enumerate(types):
        if kind in ("ES", "ET", "CS"):
            types[index] = kind = "ON"
        if kind in _STRONG:
            last_strong = kind
        elif kind == "EN" and last_strong == "L":
            types[index] = "L"
    # N1-N2 : une suite de neutres prend la direction de ses voisins forts si elle est la meme
    # (nombres comptes comme R), sinon la direction de base.
    index = 0
    while index < len(types):
        if _direction(types[index]) is not None:
            index += 1
            continue
        end = index
        while end < len(types) and _direction(types[end]) is None:
            end += 1
        # voisins forcement forts (la suite de neutres s'arrete sur eux) : `or sos` ne sert qu'au typage
        before = (_direction(types[index - 1]) or sos) if index > 0 else sos
        after = (_direction(types[end]) or sos) if end < len(types) else sos
        fill = before if before == after else sos
        for neutral in range(index, end):
            types[neutral] = fill
        index = end
    return types


def _ordered(core: str, forced_rtl: bool | None) -> str:
    clusters, isolates = _clusters(core)
    if not clusters:
        return ""
    base_rtl = bool(forced_rtl)
    if forced_rtl is None:
        for index in range(len(clusters)):
            kind = _raw_type(clusters, index, isolates)
            if kind in ("L", "R", "AL"):
                base_rtl = kind != "L"
                break
    levels: list[int] = []
    for kind in _resolved_types(clusters, isolates, base_rtl):
        if not base_rtl:
            levels.append(1 if kind == "R" else 2 if kind in _NUMBERS else 0)
        else:
            levels.append(2 if kind in ("L", "EN", "AN") else 1)
    # L4 : miroir des parentheses placees a un niveau impair.
    clusters = [
        _MIRRORS.get(cluster, cluster) if level % 2 and index not in isolates else cluster
        for index, (cluster, level) in enumerate(zip(clusters, levels))
    ]
    # L2 : du niveau le plus haut au niveau 1, chaque suite >= niveau est inversee.
    for level in range(max(levels), 0, -1):
        index = 0
        while index < len(levels):
            if levels[index] < level:
                index += 1
                continue
            end = index
            while end < len(levels) and levels[end] >= level:
                end += 1
            clusters[index:end] = clusters[index:end][::-1]
            levels[index:end] = levels[index:end][::-1]
            index = end
    return "".join(clusters)


def visual_order(text: str) -> str:
    """Ordre visuel d'un morceau de texte (identite exacte s'il ne contient aucune lettre RTL)."""
    if not _RTL_CHARACTER.search(text):
        return text
    text = text.translate(_INVISIBLE_CONTROLS)
    core = text.strip(" ")
    if not core:
        return text
    lead = len(text) - len(text.lstrip(" "))
    trail = len(text) - len(text.rstrip(" "))
    return " " * lead + _ordered(core, None) + " " * trail


def visual_strip(strip):  # type: ignore[no-untyped-def]
    """Ligne Textual (Strip) en ordre visuel. Les segments consecutifs de meme style forment un
    seul morceau : Textual coupe parfois une meme phrase en plusieurs segments (texte replie,
    notifications) ; une bordure et le contenu qu'elle entoure n'ont jamais le meme style et ne
    sont donc jamais melanges."""
    from itertools import groupby

    from rich.segment import Segment
    from textual.strip import Strip

    segments = list(strip)
    if not any(_RTL_CHARACTER.search(segment.text) for segment in segments):
        return strip
    ordered: list[Segment] = []
    for (style, control), group in groupby(segments, key=lambda segment: (segment.style, segment.control)):
        pieces = list(group)
        if control:
            ordered.extend(pieces)
            continue
        ordered.append(Segment(visual_order("".join(piece.text for piece in pieces)), style))
    return Strip(ordered, strip.cell_length)


def install_visual_reordering() -> bool:
    """Branche `visual_strip` sur le rendu ligne a ligne des widgets Textual (idempotent), AVANT
    que le compositeur ne decoupe les lignes aux bords des fenetres superposees : un morceau de
    phrase coupe n'est donc jamais ordonne seul. Retourne False si Textual n'a pas la structure
    attendue - l'affichage continue alors sans reordonnancement."""
    global _installed
    if _installed:
        return True
    try:
        from textual._styles_cache import StylesCache

        original = StylesCache.render_line

        def render_line(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            return visual_strip(original(self, *args, **kwargs))

        StylesCache.render_line = render_line  # type: ignore[method-assign]
    except Exception:  # noqa: BLE001 - structure interne de Textual modifiee : on n'empeche jamais l'affichage
        return False
    _installed = True
    return True
