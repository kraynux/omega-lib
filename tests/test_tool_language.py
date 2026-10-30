"""Socle i18n commun aux outils omega (OMEGA-SUITE_PLAN-DETAILLE_I18N.md lot 2) : langue de
l'hote, catalogue partage chaine, choix au demarrage, selecteur, redemarrage."""
from pathlib import Path

import pytest
from test_i18n import write_mo

from omega_lib.i18n.host import (
    clear_host_language,
    host_language,
    host_name,
    set_host_export_language,
    set_host_language,
)
from omega_lib.i18n.models import LanguageStatus
from omega_lib.i18n.policies import PSEUDO_LANGUAGE_CODE, SOURCE_LANGUAGE_CODE
from omega_lib.i18n.translator import ToolTranslator
from omega_lib.infrastructure.i18n.gettext_catalogs import (
    SHARED_DOMAIN,
    SHARED_LOCALE_DIR,
    CatalogError,
    discover_tool_catalogs,
    load_tool_translations,
)
from omega_lib.infrastructure.i18n.tool_language import (
    LANGUAGE_KEY,
    ToolLanguage,
    UnknownLanguageError,
)


class MemoryStore:
    def __init__(self, data: dict[str, str] | None = None) -> None:
        self.data = dict(data or {})

    def get(self, key: str, default: str | None = None) -> str | None:
        return self.data.get(key, default)

    def set(self, key: str, value: str) -> None:
        self.data[key] = value

    def all(self) -> dict[str, str]:
        return dict(self.data)


class BrokenStore(MemoryStore):
    def get(self, key: str, default: str | None = None) -> str | None:
        raise OSError("illisible")


@pytest.fixture(autouse=True)
def _no_host():
    clear_host_language()
    yield
    clear_host_language()


@pytest.fixture
def dirs(tmp_path: Path) -> tuple[Path, Path]:
    own, shared = tmp_path / "tool", tmp_path / "shared"
    write_mo(own / "en" / "LC_MESSAGES" / "omega-x.mo", {"Analyse": "Scan", "Retour": "Go back"})
    write_mo(shared / "en" / "LC_MESSAGES" / f"{SHARED_DOMAIN}.mo",
             {"Retour": "Back", "Quitter": "Quit"}, status="validated")
    write_mo(shared / "de" / "LC_MESSAGES" / f"{SHARED_DOMAIN}.mo", {"Quitter": "Beenden"})
    return own, shared


def tool(dirs: tuple[Path, Path]) -> ToolLanguage:
    own, shared = dirs
    return ToolLanguage(ToolTranslator("omega-x"), own, "OMEGA_X_LANG", shared_dir=shared)


def test_shared_catalog_is_shipped_inside_omega_lib() -> None:
    assert SHARED_LOCALE_DIR.parent.name == "omega_lib"
    assert SHARED_DOMAIN == "omega-lib"


def test_tool_catalog_wins_and_shared_catalog_fills_the_gaps(dirs) -> None:
    own, shared = dirs
    translations = load_tool_translations(own, "omega-x", "en", shared)
    assert translations.gettext("Analyse") == "Scan"
    assert translations.gettext("Retour") == "Go back"  # contexte propre a l'outil
    assert translations.gettext("Quitter") == "Quit"  # phrase commune
    assert translations.gettext("Absente") == "Absente"  # jamais vide (D9)


def test_shared_catalog_alone_is_enough(dirs) -> None:
    own, shared = dirs
    assert load_tool_translations(own, "omega-x", "de", shared).gettext("Quitter") == "Beenden"
    statuses = discover_tool_catalogs(own, "omega-x", shared)
    assert set(statuses) == {"en", "de"}
    assert statuses["en"] is LanguageStatus.TESTING  # statut du catalogue de l'outil


def test_no_catalog_at_all_raises(dirs) -> None:
    own, shared = dirs
    with pytest.raises(CatalogError):
        load_tool_translations(own, "omega-x", "ru", shared)


def test_source_and_pseudo_languages_need_no_file(dirs) -> None:
    own, shared = dirs
    assert load_tool_translations(own, "omega-x", SOURCE_LANGUAGE_CODE, shared) is None
    assert load_tool_translations(own, "omega-x", PSEUDO_LANGUAGE_CODE, shared).gettext("A") == "⟦A⟧"


def test_default_is_french(dirs) -> None:
    language = tool(dirs)
    choice = language.install(settings_store=MemoryStore(), environ={})
    assert choice.language.code == "fr"
    assert language.translator.gettext("Analyse") == "Analyse"


def test_setting_then_environment_override(dirs) -> None:
    language = tool(dirs)
    store = MemoryStore({LANGUAGE_KEY: "en"})
    language.install(settings_store=store, environ={})
    assert language.translator.gettext("Quitter") == "Quit"
    language.install(settings_store=store, environ={"OMEGA_X_LANG": "fr"})
    assert language.translator.gettext("Quitter") == "Quitter"


def test_host_language_wins_over_everything(dirs) -> None:
    set_host_language("de", "omega-suite")
    assert (host_language(), host_name()) == ("de", "omega-suite")
    language = tool(dirs)
    language.install(settings_store=MemoryStore({LANGUAGE_KEY: "en"}),
                     environ={"OMEGA_X_LANG": "fr"}, terminal_family="linux-tty")
    assert language.state.language.code == "de"
    assert language.translator.gettext("Quitter") == "Beenden"


def test_host_language_missing_for_this_tool_falls_back_to_french(dirs) -> None:
    set_host_language("ru", "omega-suite")
    language = tool(dirs)
    choice = language.install(settings_store=None, environ={})
    assert choice.language.code == "fr" and choice.fell_back_from == "ru"


def test_unreadable_settings_never_break_startup(dirs) -> None:
    assert tool(dirs).install(settings_store=BrokenStore(), environ={}).language.code == "fr"


def test_console_tty_uses_english_without_touching_the_setting(dirs) -> None:
    own, _shared = dirs
    write_mo(own / "ja" / "LC_MESSAGES" / "omega-x.mo", {"Quitter": "終了"})
    language = tool(dirs)
    store = MemoryStore({LANGUAGE_KEY: "ja"})
    language.install(settings_store=store, environ={}, terminal_family="linux-tty")
    assert language.state.language.code == "en"
    assert language.console_fallback_from == "ja"
    assert store.data[LANGUAGE_KEY] == "ja"


def test_selector_lists_french_first_and_saves_the_choice(dirs) -> None:
    language = tool(dirs)
    codes = [entry.code for entry in language.available()]
    assert codes[:3] == ["fr", "en", "de"]
    store = MemoryStore()
    language.select(store, "EN")
    assert store.data[LANGUAGE_KEY] == "en"
    language.select(store, "fr")
    assert store.data[LANGUAGE_KEY] == ""  # retour au francais = retrait de la valeur
    with pytest.raises(UnknownLanguageError):
        language.select(store, "ru")


def test_restart_environment(dirs) -> None:
    language = tool(dirs)
    environ = {"OMEGA_X_LANG": "fr"}
    language.prepare_restart_environment(environ, "en")
    assert environ == {"OMEGA_X_LANGUAGE_CHANGED": "en"}


def test_export_language(dirs) -> None:
    language = tool(dirs)
    language.install(settings_store=MemoryStore(), environ={})
    store = MemoryStore()
    assert language.export_language_override(store) is None
    language.select_export_language(store, "en")
    assert language.export_language_override(store) == "en"
    with language.translator.translating_as(language.load_state("en")):
        assert language.translator.gettext("Quitter") == "Quit"
    assert language.translator.gettext("Quitter") == "Quitter"


def test_export_state_follows_the_setting_and_never_fails(dirs) -> None:
    language = tool(dirs)
    language.install(settings_store=MemoryStore(), environ={})
    store = MemoryStore()
    assert language.export_state(store) is None  # vide = comme l'interface
    store.set("export_language", "de")
    with language.translator.translating_as(language.export_state(store)):
        assert language.translator.gettext("Quitter") == "Beenden"
        assert language.translator.html_lang() == "de"
    store.set("export_language", "ja")  # aucun catalogue : l'export reste dans la langue de l'interface
    assert language.export_state(store) is None
    assert language.export_state(BrokenStore()) is None
    assert language.export_state(None) is None


def test_host_export_language_wins_over_the_tool_setting(dirs) -> None:
    language = tool(dirs)
    language.install(settings_store=MemoryStore(), environ={})
    store = MemoryStore()
    store.set("export_language", "de")
    choice = {"code": "en"}
    set_host_export_language(lambda: choice["code"])
    assert language.export_language_setting(store) == "en"
    assert language.export_language_override(store) == "en"
    choice["code"] = ""  # relu a chaque export : effet immediat
    assert language.export_state(store) is None
    clear_host_language()
    assert language.export_language_override(store) == "de"


def test_lazy_text_is_recomposed_in_the_export_language(dirs) -> None:
    language = tool(dirs)
    language.install(settings_store=MemoryStore(), environ={})
    text = language.translator.lazy("Quitter")
    assert text == "Quitter"
    with language.translator.translating_as(language.load_state("de")):
        assert language.translator.retranslate(text) == "Beenden"
        assert language.translator.html_lang() == "de"


def test_log_line_stays_french_in_the_file_and_is_translated_on_screen(dirs) -> None:
    import logging

    language = tool(dirs)
    language.install(settings_store=MemoryStore({LANGUAGE_KEY: "de"}), environ={})
    translator = language.translator
    line = translator.log_text("Quitter {n}", n=3)
    record = logging.LogRecord("x", logging.INFO, __file__, 1, line, None, None)
    assert record.getMessage() == "Quitter 3"  # fichier journal : francais
    assert translator.log_message(record.msg, record.args) == "Quitter 3"  # pas de traduction de "Quitter {n}"
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "Quitter", None, None)
    assert translator.log_message(record.msg, record.args) == "Beenden"
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "Quitter %s", ("x",), None)
    assert translator.log_message(record.msg, record.args) == "Quitter x"
