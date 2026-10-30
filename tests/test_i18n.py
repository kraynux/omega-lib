import struct
from pathlib import Path

import pytest

from omega_lib.i18n.models import LanguageStatus
from omega_lib.i18n.policies import (
    PSEUDO_LANGUAGE_CODE,
    SOURCE_LANGUAGE_CODE,
    console_fallback_language,
    text_direction,
    normalize_language_code,
    ordered_languages,
    resolve_language,
)
from omega_lib.i18n.service import TranslationState, mark
from omega_lib.infrastructure.i18n.gettext_catalogs import (
    CatalogError,
    discover_catalogs,
    load_translations,
)


def write_mo(path: Path, messages: dict[str, str], status: str | None = None) -> None:
    """Catalogue GNU .mo minimal (format documente de gettext) - sans msgfmt."""
    header = "Content-Type: text/plain; charset=UTF-8\nPlural-Forms: nplurals=2; plural=(n != 1);\n"
    if status:
        header += f"X-Omega-Status: {status}\n"
    entries = sorted({"": header, **messages}.items())
    ids = b"".join(k.encode() + b"\0" for k, _ in entries)
    strs = b"".join(v.encode() + b"\0" for _, v in entries)
    count = len(entries)
    key_start = 7 * 4 + 16 * count
    value_start = key_start + len(ids)
    offsets: list[int] = []
    pos = 0
    for key, _ in entries:
        offsets += [len(key.encode()), key_start + pos]
        pos += len(key.encode()) + 1
    pos = 0
    for _, value in entries:
        offsets += [len(value.encode()), value_start + pos]
        pos += len(value.encode()) + 1
    table = struct.pack("Iiiiiii", 0x950412DE, 0, count, 7 * 4, 7 * 4 + 8 * count, 0, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(table + struct.pack(f"{len(offsets)}i", *offsets) + ids + strs)


def test_normalize_language_code() -> None:
    assert normalize_language_code("EN") == "en"
    assert normalize_language_code("zh-cn") == "zh_CN"
    assert normalize_language_code("ru_RU.UTF-8") == "ru"
    assert normalize_language_code(" x-test ") == PSEUDO_LANGUAGE_CODE
    assert normalize_language_code("") == ""
    assert normalize_language_code(None) == ""


def test_source_language_always_first_and_order_of_lots() -> None:
    available = {"zh_CN": LanguageStatus.TESTING, "sv": LanguageStatus.TESTING,
                 "en": LanguageStatus.VALIDATED, "ru": LanguageStatus.TESTING}
    codes = [lang.code for lang in ordered_languages(available, include_pseudo=True)]
    assert codes == ["fr", "en", "ru", "zh_CN", "sv", PSEUDO_LANGUAGE_CODE]


def test_source_language_present_without_any_catalog() -> None:
    languages = ordered_languages({}, include_pseudo=False)
    assert [lang.code for lang in languages] == [SOURCE_LANGUAGE_CODE]
    assert languages[0].native_name == "Français"
    assert languages[0].status is LanguageStatus.SOURCE


def test_native_names_are_shown_in_their_own_language() -> None:
    names = {lang.code: lang.native_name for lang in ordered_languages(
        {c: LanguageStatus.TESTING for c in ("en", "es", "ru", "zh_CN")}, include_pseudo=False)}
    assert names == {"fr": "Français", "en": "English", "es": "Español", "ru": "Русский", "zh_CN": "简体中文"}


def test_hindi_and_arabic_follow_the_lot_order() -> None:
    languages = ordered_languages(
        {c: LanguageStatus.TESTING for c in ("ar", "hi", "zh_CN", "en")}, include_pseudo=False)
    assert [(lang.code, lang.native_name) for lang in languages] == [
        ("fr", "Français"), ("en", "English"), ("zh_CN", "简体中文"), ("hi", "हिन्दी"), ("ar", "العربية")]


@pytest.mark.parametrize("requested", ["", None, "fr", "FR"])
def test_resolve_source_language_without_fallback(requested: str | None) -> None:
    choice = resolve_language(requested, available=["en"])
    assert choice.language.code == SOURCE_LANGUAGE_CODE
    assert choice.fell_back_from is None


def test_resolve_unavailable_language_falls_back_to_source() -> None:
    choice = resolve_language("ru", available=["en"])
    assert choice.language.code == SOURCE_LANGUAGE_CODE
    assert choice.fell_back_from == "ru"


def test_resolve_available_language_with_status() -> None:
    choice = resolve_language("en", available=["en"], statuses={"en": LanguageStatus.VALIDATED})
    assert (choice.language.code, choice.language.status) == ("en", LanguageStatus.VALIDATED)


def test_pseudo_language_always_offered() -> None:
    assert resolve_language(PSEUDO_LANGUAGE_CODE, available=[]).language.code == PSEUDO_LANGUAGE_CODE


def test_translation_state_defaults_to_identity() -> None:
    state = TranslationState()
    assert state.gettext("Retour") == "Retour"
    assert state.ngettext("{n} entree", "{n} entrees", 3) == "{n} entrees"
    assert state.language.code == SOURCE_LANGUAGE_CODE


def test_pseudo_translation_wraps_and_keeps_placeholders(tmp_path: Path) -> None:
    state = TranslationState()
    state.install(resolve_language(PSEUDO_LANGUAGE_CODE, []).language,
                  load_translations(tmp_path, "omega-x", PSEUDO_LANGUAGE_CODE))
    assert state.gettext("Bonjour {nom}").format(nom="A") == "⟦Bonjour A⟧"
    assert state.ngettext("{n} entree", "{n} entrees", 1) == "⟦{n} entree⟧"
    state.reset()
    assert state.gettext("Retour") == "Retour"


def test_mark_does_not_translate() -> None:
    assert mark("Retour") == "Retour"


def test_real_catalog_is_discovered_loaded_and_used(tmp_path: Path) -> None:
    write_mo(tmp_path / "en" / "LC_MESSAGES" / "omega-x.mo",
             {"Retour": "Back", "{n} entree\0{n} entrees": "{n} entry\0{n} entries"}, status="validated")
    write_mo(tmp_path / "es" / "LC_MESSAGES" / "omega-x.mo", {"Retour": "Volver"})
    found = discover_catalogs(tmp_path, "omega-x")
    assert found == {"en": LanguageStatus.VALIDATED, "es": LanguageStatus.TESTING}
    state = TranslationState()
    state.install(resolve_language("en", found, found).language, load_translations(tmp_path, "omega-x", "en"))
    assert state.gettext("Retour") == "Back"
    assert state.gettext("Phrase non traduite") == "Phrase non traduite"
    assert state.ngettext("{n} entree", "{n} entrees", 2) == "{n} entries"


def test_other_tool_catalog_is_ignored(tmp_path: Path) -> None:
    write_mo(tmp_path / "en" / "LC_MESSAGES" / "omega-autre.mo", {"Retour": "Back"})
    assert discover_catalogs(tmp_path, "omega-x") == {}


def test_missing_or_corrupt_catalog_raises_catalog_error(tmp_path: Path) -> None:
    with pytest.raises(CatalogError):
        load_translations(tmp_path, "omega-x", "en")
    broken = tmp_path / "ru" / "LC_MESSAGES" / "omega-x.mo"
    broken.parent.mkdir(parents=True)
    broken.write_bytes(b"pas un catalogue")
    assert discover_catalogs(tmp_path, "omega-x") == {"ru": LanguageStatus.TESTING}
    with pytest.raises(CatalogError):
        load_translations(tmp_path, "omega-x", "ru")


def test_missing_locale_dir_means_no_catalog(tmp_path: Path) -> None:
    assert discover_catalogs(tmp_path / "absent", "omega-x") == {}
    assert load_translations(tmp_path / "absent", "omega-x", SOURCE_LANGUAGE_CODE) is None


@pytest.mark.parametrize("code", ["vi", "zh_CN", "th", "ja", "ko", "hi", "ar"])
def test_console_tty_falls_back_to_english_for_wide_scripts(code: str) -> None:
    assert console_fallback_language(code, "linux-tty") == "en"


@pytest.mark.parametrize(("code", "family"), [
    ("ru", "linux-tty"), ("fr", "linux-tty"), ("hi", "terminator"), ("zh_CN", "kitty"), ("ar", None), ("vi", "konsole"), ("pl", "linux-tty"),
])
def test_no_console_fallback_when_the_script_can_be_shown(code: str, family: str | None) -> None:
    assert console_fallback_language(code, family) is None


def test_only_arabic_is_written_right_to_left() -> None:
    assert text_direction("ar") == "rtl"
    assert [text_direction(c) for c in ("fr", "en", "hi", "zh_CN", "ru")] == ["ltr"] * 5


def test_final_language_order():
    codes = [language.code for language in ordered_languages(
        {c: LanguageStatus.TESTING for c in ("ar", "ja", "de", "pt_BR", "en")}, include_pseudo=False)]
    assert codes == ["fr", "en", "pt_BR", "de", "ja", "ar"]
    assert normalize_language_code("pt-br") == "pt_BR"
    assert normalize_language_code("de_DE.UTF-8") == "de"
    assert console_fallback_language("de", "linux-tty") is None
    assert console_fallback_language("pt_BR", "linux-tty") is None


def test_seventeen_languages_final_list():
    from omega_lib.i18n.policies import PREFERRED_ORDER, NATIVE_NAMES
    assert PREFERRED_ORDER == ("fr", "en", "es", "pt_BR", "it", "de", "nl", "pl", "ru", "zh_CN", "vi", "th", "id", "ja", "ko", "hi", "ar")
    assert all(code in NATIVE_NAMES for code in PREFERRED_ORDER)
