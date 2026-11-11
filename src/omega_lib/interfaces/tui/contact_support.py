# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Aide -> « Contact et support » et « Se declarer utilisateur (anonyme) », ecrans Textual
partages par les outils omega (D-016, 2026-11-09). Repris d'omega-log 1.6.0 (lui-meme porte
d'omega-serv 2.6.0) : memes sections, memes boutons, memes textes ; seul le nom du logiciel change.

- Payer un cafe (PayPal) ; se declarer utilisateur anonyme, UNE SEULE FOIS (aucun de ces outils n'a
  de service permanent) ; contacter le support (mail et formulaire du site, aucun formulaire ici) ;
  version et mises a jour (lecture de download/sha.txt, jamais sans clic).
- Les adresses sont toujours affichees en clair : sans session graphique (SSH), le navigateur ne
  s'ouvre pas et l'utilisateur les recopie.
- Envois et lectures dans un fil : l'ecran ne se fige jamais (5 s au plus).

Integration (un outil) : son ecran d'aide pousse `ContactSupportKit(...).screen()`. Le kit recoit la
classe d'ecran de base DE L'OUTIL (Echap -> Retour traduit dans le pied de page, fleches), sa
fonction de traduction `_` (catalogue de l'outil chaine au catalogue partage omega-lib, ou sont
ces phrases) et la langue active (noms de pays)."""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import cache
from importlib import resources
from typing import Any, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Center, Container, Horizontal, Middle, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Header, Select, Static

from omega_lib.declaration.countries import COUNTRY_CODES
from omega_lib.declaration.models import (
    CONTACT_FORM_URL,
    OTHER,
    PAYPAL_URL,
    RECEPTION_URL,
    SUPPORT_MAIL,
    UpdateCheck,
    UpdateStatus,
)
from omega_lib.declaration.service import (
    DeclareResult,
    WithdrawResult,
    check_for_update,
    declare,
    preview_payload,
    withdraw,
)
from omega_lib.i18n.service import mark as N_
from omega_lib.ports.declaration import ContactSupportServices

_CONTINENT_LABELS = (
    ("AF", N_("Afrique")),
    ("AN", N_("Antarctique")),
    ("AS", N_("Asie")),
    ("EU", N_("Europe")),
    ("NA", N_("Amérique du Nord")),
    ("OC", N_("Océanie")),
    ("SA", N_("Amérique du Sud")),
)


def local_date(value: datetime | None) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M") if value is not None else "-"


@cache
def _country_names() -> dict[str, dict[str, str]]:
    data = resources.files("omega_lib.declaration").joinpath("country_names.json").read_text(encoding="utf-8")
    names = json.loads(data)["names"]
    return names if isinstance(names, dict) else {}


def country_options(language_code: str, other_label: str) -> list[tuple[str, str]]:
    """(libelle, code) tries par nom dans la langue de l'interface ; « Autre » en dernier."""
    names = _country_names()
    table = names.get(language_code) or names.get("fr") or {}
    options = sorted(((table.get(code, code), code) for code in COUNTRY_CODES), key=lambda item: item[0].casefold())
    return [*options, (other_label, OTHER)]


@dataclass(frozen=True)
class ContactSupportKit:
    """Tout ce qu'il faut pour ouvrir les ecrans dans un outil donne."""

    services: ContactSupportServices
    translate: Callable[[str], str]
    language_code: Callable[[], str]
    base_screen: type[Screen[Any]] = Screen

    def screen(self) -> Screen[Any]:
        screen_class: Any = _screen_class(_ContactSupportView, self.base_screen)
        return screen_class(kit=self)  # type: ignore[no-any-return]

    def declaration_screen(self) -> Screen[Any]:
        screen_class: Any = _screen_class(_DeclarationView, self.base_screen)
        return screen_class(kit=self)  # type: ignore[no-any-return]


@cache
def _screen_class(view: type, base: type[Screen[Any]]) -> type[Screen[Any]]:
    """Ecran = vue partagee + base de l'outil (nom de classe stable pour les CSS et les tests)."""
    name = view.__name__.lstrip("_").replace("View", "Screen")
    return type(name, (view, base), {"__module__": __name__})


class ConfirmWithdrawScreen(ModalScreen[bool]):
    """Modale de confirmation (meme patron que confirm.py des outils, sans pied de page)."""

    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "cancel", "Annuler", show=False)]

    def __init__(self, *, kit: ContactSupportKit) -> None:
        super().__init__()
        self._kit = kit

    def compose(self) -> ComposeResult:
        _ = self._kit.translate
        with Middle(), Center(), Vertical(classes="omega-confirm-box"):
            yield Static(_("NE PLUS ME DÉCLARER ?"), classes="omega-confirm-title")
            yield Static(_("Votre entrée sera supprimée du compteur et la clé effacée de cette installation."))
            with Horizontal(classes="omega-confirm-buttons"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Confirmer"), id="confirm", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Annuler"), id="cancel", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(event.button.id == "confirm")

    def action_cancel(self) -> None:
        self.dismiss(False)


class _ContactSupportView:
    """Aide -> Contact et support (vue ; l'ecran reel herite aussi de la base de l'outil)."""

    app: Any
    query_one: Any
    run_worker: Any
    dismiss: Any

    def __init__(self, *, kit: ContactSupportKit, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._kit = kit
        self._release_notes_url = ""

    def compose(self) -> ComposeResult:
        _ = self._kit.translate
        services = self._kit.services
        yield Header()
        with VerticalScroll(classes="omega-panel"):
            with Center():
                yield Static(_("CONTACT ET SUPPORT"), classes="omega-title")
            yield Static(_("Aidez le développeur : {software} est développé et maintenu par une seule "
                           "personne.").format(software=services.software), classes="omega-hint")

            yield Static(_("Payer un café"), classes="omega-subtitle")
            yield Static(_("Un don aide à couvrir les frais des serveurs (électricité)."), classes="omega-hint")
            yield Static(PAYPAL_URL)
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button(_("Payer un café"), id="coffee", variant="primary")

            yield Static(_("Se déclarer utilisateur (anonyme)"), classes="omega-subtitle")
            yield Static(_("Une déclaration volontaire et anonyme, qui sert uniquement à compter les "
                           "utilisateurs et, si vous le souhaitez, leur continent ou leur pays."),
                         classes="omega-hint")
            yield Static("", id="declaration-state")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Se déclarer utilisateur (anonyme)"), id="declare", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Ne plus me déclarer"), id="withdraw", variant="error", disabled=True)

            yield Static(_("Contacter le support"), classes="omega-subtitle")
            yield Static(_("Mail : {SUPPORT_MAIL}").format(SUPPORT_MAIL=SUPPORT_MAIL))
            yield Static(_("Formulaire de contact : {CONTACT_FORM_URL}").format(CONTACT_FORM_URL=CONTACT_FORM_URL))
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button(_("Contacter le support"), id="contact", variant="primary")

            yield Static(_("Version et mises à jour"), classes="omega-subtitle")
            yield Static(_("Compare votre version à la liste des versions publiées sur le site. Rien n'est "
                           "envoyé, et rien n'est vérifié sans votre clic."), classes="omega-hint")
            yield Static(_("Version installée : {version}").format(version=services.version), id="update-state")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Vérifier les mises à jour"), id="check-update", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Voir les nouveautés"), id="release-notes", disabled=True)
        with Center(), Horizontal(classes="omega-actions omega-fixed-actions"), Container(classes="omega-btn-frame"):
            yield Button(_("Retour"), id="back")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        _ = self._kit.translate
        try:
            state = self.query_one("#declaration-state", Static)
            declare_button = self.query_one("#declare", Button)
            withdraw_button = self.query_one("#withdraw", Button)
        except NoMatches:
            return  # ecran deja ferme
        stored = self._kit.services.store.load()
        if stored is None:
            state.update(_("État : non déclaré."))
            declare_button.label = _("Se déclarer utilisateur (anonyme)")
            withdraw_button.disabled = True
            return
        state.update(_("État : déclaré le {value} (envoi : une seule fois).").format(
            value=local_date(stored.declared_at)))
        declare_button.label = _("Modifier ma déclaration")
        withdraw_button.disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        event.stop()
        if button_id == "back":
            self.dismiss()
        elif button_id == "coffee":
            self._open(PAYPAL_URL)
        elif button_id == "contact":
            self._open(CONTACT_FORM_URL)
        elif button_id == "check-update":
            self._check_update()
        elif button_id == "release-notes" and self._release_notes_url:
            self._open(self._release_notes_url)
        elif button_id == "declare":
            self.app.push_screen(self._kit.declaration_screen(), lambda _result: self._refresh())
        elif button_id == "withdraw":
            self.app.push_screen(ConfirmWithdrawScreen(kit=self._kit), self._withdraw_if_confirmed)

    def _open(self, url: str) -> None:
        _ = self._kit.translate
        self.app.notify(_("Ouverture dans le navigateur..."))
        self.run_worker(lambda: self._open_in_thread(url), thread=True, exclusive=True)

    def _open_in_thread(self, url: str) -> None:
        _ = self._kit.translate
        if not self._kit.services.open_url(url):
            self.app.call_from_thread(
                self.app.notify,
                _("Aucun navigateur disponible ici (session sans affichage) : ouvrez cette adresse vous-même : "
                  "{url}").format(url=url),
                severity="warning", timeout=15,
            )

    def _withdraw_if_confirmed(self, confirmed: bool | None) -> None:
        if not confirmed:
            return
        self.query_one("#withdraw", Button).disabled = True
        services = self._kit.services
        self.run_worker(
            lambda: self.app.call_from_thread(self._finish_withdraw, withdraw(services.store, services.sender)),
            thread=True, exclusive=True,
        )

    def _finish_withdraw(self, result: WithdrawResult) -> None:
        _ = self._kit.translate
        if result.reception_reached:
            self.app.notify(_("Vous n'êtes plus déclaré : votre entrée est supprimée et la clé effacée."))
        else:
            self.app.notify(_("Clé effacée. Réception injoignable : votre entrée y disparaîtra seule (1 an)."),
                            severity="warning", timeout=12)
        self._refresh()

    def _check_update(self) -> None:
        _ = self._kit.translate
        self.query_one("#check-update", Button).disabled = True
        self.query_one("#update-state", Static).update(_("Vérification en cours..."))
        services = self._kit.services
        self.run_worker(
            lambda: self.app.call_from_thread(
                self._show_update, check_for_update(services.release_source, services.software, services.version)),
            thread=True, exclusive=True,
        )

    def _show_update(self, check: UpdateCheck) -> None:
        _ = self._kit.translate
        try:
            state = self.query_one("#update-state", Static)
            notes = self.query_one("#release-notes", Button)
            self.query_one("#check-update", Button).disabled = False
        except NoMatches:
            return  # ecran deja ferme
        self._release_notes_url = ""
        notes.disabled = True
        if check.status is UpdateStatus.UPDATE_AVAILABLE:
            self._release_notes_url = check.notes_url
            notes.disabled = False
            state.update(_("Nouvelle version disponible : {latest} (installée : {installed}).\nArchive : {url}").format(
                latest=check.latest, installed=check.installed, url=check.archive_url))
        elif check.status is UpdateStatus.UP_TO_DATE:
            state.update(_("Vous avez la dernière version publiée ({version}).").format(version=check.installed))
        elif check.status is UpdateStatus.AHEAD:
            state.update(_("Votre version ({installed}) est plus récente que la dernière publiée ({latest}) : "
                           "version en cours, pas encore publiée.").format(
                               installed=check.installed, latest=check.latest))
        else:
            state.update(_("Version installée : {version}. Site injoignable ou liste des versions illisible : "
                           "réessayez plus tard.").format(version=check.installed))


class _DeclarationView:
    """Aide -> Contact et support -> Se declarer utilisateur : continent et pays facultatifs (deux
    listes independantes, chacune avec « Autre »), puis le message EXACT qui sera envoye, mis a
    jour a chaque choix. Envoi : une seule fois, maintenant."""

    app: Any
    query_one: Any
    run_worker: Any
    dismiss: Any

    def __init__(self, *, kit: ContactSupportKit, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._kit = kit
        self._existing = kit.services.store.load()

    def compose(self) -> ComposeResult:
        _ = self._kit.translate
        existing = self._existing.declaration if self._existing is not None else None
        other = _("Autre (non référencé)")
        continents = [*((_(label), code) for code, label in _CONTINENT_LABELS), (other, OTHER)]
        yield Header()
        with VerticalScroll(classes="omega-panel"):
            with Center():
                yield Static(_("SE DÉCLARER UTILISATEUR (ANONYME)"), classes="omega-title")
            yield Static(_("Une déclaration volontaire et anonyme : elle sert uniquement à compter les "
                           "utilisateurs d'{software} et, si vous le souhaitez, leur continent ou leur pays. "
                           "Une clé tirée au hasard est créée pour cette installation ; elle n'a aucun lien "
                           "avec vous ni avec votre machine. Envoi : une seule fois, maintenant.").format(
                               software=self._kit.services.software), classes="omega-hint")

            yield Static(_("Continent (facultatif)"), classes="omega-subtitle")
            yield Select(continents, value=existing.continent if existing and existing.continent else Select.NULL,
                         allow_blank=True, prompt=_("Non précisé"), id="declaration-continent")
            yield Static(_("Pays (facultatif)"), classes="omega-subtitle")
            yield Select(country_options(self._kit.language_code(), other),
                         value=existing.country if existing and existing.country else Select.NULL,
                         allow_blank=True, prompt=_("Non précisé"), id="declaration-country")

            yield Static(_("Message envoyé"), classes="omega-subtitle")
            yield Static("", id="declaration-preview")
            yield Static(_("Destination : {RECEPTION_URL}").format(RECEPTION_URL=RECEPTION_URL), classes="omega-hint")
            yield Static(_("Jamais envoyés : votre nom, le nom de la machine, vos réglages, vos cibles ni vos "
                           "résultats."), classes="omega-hint")
            yield Static(_("Votre adresse IP n'est pas enregistrée dans les déclarations. Comme pour toute visite "
                           "d'un site, elle passe par les contrôles de sécurité et le journal technique du serveur "
                           "de réception."), classes="omega-hint")
            yield Static(_("Vous pouvez retirer votre déclaration à tout moment depuis Contact et support."),
                         classes="omega-hint")
            yield Static("", id="declaration-error", classes="omega-hint")
        with Center(), Horizontal(classes="omega-actions omega-fixed-actions"):
            with Container(classes="omega-btn-frame"):
                yield Button(_("Envoyer"), id="send", variant="primary")
            with Container(classes="omega-btn-frame"):
                yield Button(_("Annuler"), id="back")
        yield Footer()

    def on_mount(self) -> None:
        self._update_preview()

    def _value(self, widget_id: str) -> str:
        value = self.query_one(f"#{widget_id}", Select).value
        return "" if value is Select.NULL or value is None else str(value)

    def on_select_changed(self, _event: Select.Changed) -> None:
        self._update_preview()

    def _update_preview(self) -> None:
        services = self._kit.services
        payload = preview_payload(services.store, services.software, services.version,
                                  self._value("declaration-continent"), self._value("declaration-country"))
        _ = self._kit.translate
        if self._existing is None:
            payload["cle"] = _("<clé tirée au hasard à l'envoi>")
        self.query_one("#declaration-preview", Static).update(json.dumps(payload, ensure_ascii=False))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "back":
            self.dismiss()
        elif event.button.id == "send":
            self._send()

    def _send(self) -> None:
        continent, country = self._value("declaration-continent"), self._value("declaration-country")
        services = self._kit.services
        _ = self._kit.translate
        self.query_one("#send", Button).disabled = True
        self.query_one("#declaration-error", Static).update(_("Envoi en cours..."))

        def run() -> None:
            result = declare(services.store, services.sender, services.software, services.version, continent, country)
            self.app.call_from_thread(self._finish, result)

        self.run_worker(run, thread=True, exclusive=True)

    def _finish(self, result: DeclareResult) -> None:
        _ = self._kit.translate
        if result.ok:
            self.app.notify(_("Merci ! Vous êtes déclaré utilisateur anonyme."))
            self.dismiss()
            return
        try:
            self.query_one("#send", Button).disabled = False
            self.query_one("#declaration-error", Static).update(
                _("Réception injoignable : rien n'a été enregistré, réessayez plus tard."))
        except NoMatches:
            return
