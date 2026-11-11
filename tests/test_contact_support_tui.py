# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecrans partages « Contact et support » / « Se declarer » (D-016). Jamais de vrai envoi ni de
vrai navigateur : faux expediteur, fausse source, faux ouvreur."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import ClassVar

import pytest

textual = pytest.importorskip("textual")

from textual.app import App
from textual.binding import Binding, BindingType
from textual.screen import Screen
from textual.widgets import Button, Select, Static

from omega_lib.infrastructure.declaration.json_store import JsonDeclarationStore
from omega_lib.interfaces.tui.contact_support import (
    ContactSupportKit,
    country_options,
)
from omega_lib.ports.declaration import ContactSupportServices, SendOutcome


class _Sender:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    def send(self, payload: dict) -> SendOutcome:
        self.sent.append(payload)
        return SendOutcome(True)


class _Source:
    def fetch_sha_list(self) -> str | None:
        return "x  omega-check-1.5.0.tar.gz\ny  omega-check-1.6.0.tar.gz\n"


class _ToolBase(Screen[None]):
    """Base d'ecran d'un outil (Echap -> retour, comme les OmegaScreen)."""

    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "back", "Retour", show=True)]

    def action_back(self) -> None:
        self.dismiss()


class _Host(App[None]):
    def __init__(self, kit: ContactSupportKit) -> None:
        super().__init__()
        self._kit = kit

    def on_mount(self) -> None:
        self.push_screen(self._kit.screen())


def _kit(tmp_path: Path, opened: list[str]) -> ContactSupportKit:
    services = ContactSupportServices(
        software="omega-check", version="1.5.0", store=JsonDeclarationStore(tmp_path / "declaration.json"),
        sender=_Sender(), release_source=_Source(), open_url=lambda url: opened.append(url) is not None,
    )
    return ContactSupportKit(services=services, translate=lambda text: text, language_code=lambda: "de",
                             base_screen=_ToolBase)


async def _settle(pilot) -> None:
    await pilot.pause()
    await asyncio.sleep(0.2)
    await pilot.pause()


def test_screen_inherits_the_tool_base_and_shows_addresses(tmp_path: Path) -> None:
    kit = _kit(tmp_path, [])
    screen = kit.screen()
    assert isinstance(screen, _ToolBase) and type(screen).__name__ == "ContactSupportScreen"
    assert type(kit.declaration_screen()).__name__ == "DeclarationScreen"

    async def scenario() -> None:
        app = _Host(kit)
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            texts = " ".join(str(w.render()) for w in app.screen.query(Static))
            for text in ("https://paypal.me/kraynux", "kraynux@proton.me",
                         "https://kraynux.snake-mackarel.ts.net/contact/", "omega-check est développé",
                         "non déclaré", "Version installée : 1.5.0"):
                assert text in texts
            assert app.screen.query_one("#withdraw", Button).disabled

    asyncio.run(scenario())


def test_declare_once_then_withdraw(tmp_path: Path) -> None:
    kit = _kit(tmp_path, [])
    sender = kit.services.sender

    async def scenario() -> None:
        app = _Host(kit)
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            contact = app.screen
            contact.query_one("#declare", Button).press()
            await pilot.pause()
            declaration = app.screen
            assert type(declaration).__name__ == "DeclarationScreen"
            declaration.query_one("#declaration-continent", Select).value = "EU"
            declaration.query_one("#declaration-country", Select).value = "FR"
            await pilot.pause()
            preview = str(declaration.query_one("#declaration-preview", Static).render())
            assert '"logiciel": "omega-check"' in preview and '"envoi": "unique"' in preview
            assert "<clé tirée au hasard à l'envoi>" in preview
            declaration.query_one("#send", Button).press()
            await _settle(pilot)
            assert app.screen is contact
            assert "déclaré le" in str(contact.query_one("#declaration-state", Static).render())
            assert not contact.query_one("#withdraw", Button).disabled

            contact.query_one("#withdraw", Button).press()
            await pilot.pause()
            app.screen.query_one("#confirm", Button).press()
            await _settle(pilot)
            assert app.screen is contact
            assert "non déclaré" in str(contact.query_one("#declaration-state", Static).render())

    asyncio.run(scenario())
    assert sender.sent[0]["logiciel"] == "omega-check" and sender.sent[0]["continent"] == "EU"
    assert sender.sent[0]["pays"] == "FR" and sender.sent[0]["envoi"] == "unique"
    assert sender.sent[1] == {"cle": sender.sent[0]["cle"], "retrait": True}
    assert not (tmp_path / "declaration.json").exists()


def test_update_check_and_browser_buttons(tmp_path: Path) -> None:
    opened: list[str] = []
    kit = _kit(tmp_path, opened)

    async def scenario() -> None:
        app = _Host(kit)
        async with app.run_test(size=(120, 50)) as pilot:
            await pilot.pause()
            screen = app.screen
            screen.query_one("#check-update", Button).press()
            await _settle(pilot)
            state = str(screen.query_one("#update-state", Static).render())
            assert "1.6.0" in state and "omega-check-1.6.0.tar.gz" in state
            assert not screen.query_one("#release-notes", Button).disabled
            screen.query_one("#release-notes", Button).press()
            await _settle(pilot)
            screen.query_one("#coffee", Button).press()
            await _settle(pilot)
            screen.query_one("#contact", Button).press()
            await _settle(pilot)

    asyncio.run(scenario())
    assert "https://paypal.me/kraynux" in opened
    assert "https://kraynux.snake-mackarel.ts.net/contact/" in opened


def test_country_names_follow_the_interface_language() -> None:
    german = {code: label for label, code in country_options("de", "Andere")}
    assert german["DE"] == "Deutschland" and german["autre"] == "Andere"
    french = {code: label for label, code in country_options("xx", "Autre")}
    assert french["DE"] == "Allemagne"
    assert len(german) == 250
