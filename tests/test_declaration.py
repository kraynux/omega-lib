# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""« Contact et support » partage (D-016, 2026-11-09) : message, version, cas d'usage, stockage,
mises a jour. Jamais de vrai envoi : faux expediteur, fausse source."""
from __future__ import annotations

import os
import stat
from datetime import datetime, timezone
from pathlib import Path

import pytest

from omega_lib.declaration.countries import COUNTRY_CODES
from omega_lib.declaration.models import SOFTWARES, Declaration, UpdateStatus
from omega_lib.declaration.policies import (
    build_payload,
    build_withdrawal,
    compare_with_published,
    declaration_errors,
    download_base_url,
    is_valid_version,
    published_versions,
    sha_list_url,
    wire_version,
)
from omega_lib.declaration.service import check_for_update, declare, preview_payload, withdraw
from omega_lib.infrastructure.declaration import build_contact_support
from omega_lib.infrastructure.declaration.json_store import JsonDeclarationStore
from omega_lib.ports.declaration import SendOutcome

KEY = "0123456789abcdef0123456789abcdef"
RECEPTION_PHP = Path.home() / "DEV/SERV/compteur-reception/index.php"


class _Sender:
    def __init__(self, ok: bool = True) -> None:
        self.ok = ok
        self.sent: list[dict] = []

    def send(self, payload: dict) -> SendOutcome:
        self.sent.append(payload)
        return SendOutcome(self.ok, "" if self.ok else "unreachable")


class _Source:
    def __init__(self, text: str | None) -> None:
        self.text = text

    def fetch_sha_list(self) -> str | None:
        return self.text


def test_payload_names_the_software_and_is_always_once() -> None:
    assert build_payload(Declaration(KEY, "EU", "FR"), "omega-scan", "2.5.0") == {
        "cle": KEY, "logiciel": "omega-scan", "version": "2.5.0", "envoi": "unique", "continent": "EU", "pays": "FR",
    }
    assert "pays" not in build_payload(Declaration(KEY), "omega-check", "1.5.0")
    assert "continent" not in build_payload(Declaration(KEY), "omega-check", "1.5.0")


def test_unknown_software_is_refused_before_sending() -> None:
    with pytest.raises(ValueError):
        build_payload(Declaration(KEY), "omega-inconnu", "1.0.0")


def test_two_part_version_is_sent_as_three_parts() -> None:
    """La reception exige X.Y.Z : omega-fire affiche « 3.5 »."""
    assert wire_version("3.5") == "3.5.0"
    assert wire_version("1.5.0") == "1.5.0"
    assert wire_version("3") == "3.0.0"
    assert wire_version("dev") == "0.0.0"
    assert wire_version("1.2.3.4") == "0.0.0"
    assert all(is_valid_version(wire_version(v)) for v in ("3.5", "1.5.0", "x", "10.20.30"))
    assert build_payload(Declaration(KEY), "omega-fire", "3.5")["version"] == "3.5.0"


def test_invalid_fields_are_named() -> None:
    assert declaration_errors(Declaration("court")) == ["cle"]
    assert declaration_errors(Declaration(KEY, "XX", "ZZ")) == ["continent", "pays"]
    assert declaration_errors(Declaration(KEY, "autre", "autre")) == []
    assert build_withdrawal(KEY) == {"cle": KEY, "retrait": True}


def test_closed_lists_match_the_reception_script() -> None:
    """Meme liste de logiciels et de pays que index.php (sinon 400 a la reception)."""
    if not RECEPTION_PHP.is_file():
        pytest.skip("script de reception absent de cette machine")
    php = RECEPTION_PHP.read_text(encoding="utf-8")
    softwares_block = php.split("const SOFTWARES", 1)[1].split("];", 1)[0]
    countries_block = php.split("const COUNTRIES", 1)[1].split("];", 1)[0]
    for name in SOFTWARES:
        assert f"'{name}'" in softwares_block
    for code in COUNTRY_CODES:
        assert f"'{code}'" in countries_block
    assert len(COUNTRY_CODES) == 249


def test_declare_once_keeps_the_key_and_saves_only_on_success(tmp_path: Path) -> None:
    store = JsonDeclarationStore(tmp_path / "declaration.json")
    failing = _Sender(ok=False)
    result = declare(store, failing, "omega-deep", "1.5.0", "EU", key_factory=lambda: KEY)
    assert not result.ok and result.reason == "unreachable"
    assert store.load() is None

    sender = _Sender()
    when = datetime(2026, 11, 9, tzinfo=timezone.utc)
    assert declare(store, sender, "omega-deep", "1.5.0", "EU", "FR", key_factory=lambda: KEY, now=lambda: when).ok
    stored = store.load()
    assert stored is not None and stored.declaration == Declaration(KEY, "EU", "FR") and stored.declared_at == when
    # Second envoi (changement de pays) : meme cle, date de premiere declaration gardee.
    assert declare(store, sender, "omega-deep", "1.5.0", "", "BE", key_factory=lambda: "f" * 32).ok
    again = store.load()
    assert again is not None and again.declaration.key == KEY and again.declared_at == when
    assert [p["cle"] for p in sender.sent] == [KEY, KEY]
    assert stat.S_IMODE(os.stat(tmp_path / "declaration.json").st_mode) == 0o600


def test_preview_shows_the_exact_message(tmp_path: Path) -> None:
    store = JsonDeclarationStore(tmp_path / "declaration.json")
    assert preview_payload(store, "omega-fuzz", "1.5.0", "", "FR") == {
        "cle": "0" * 32, "logiciel": "omega-fuzz", "version": "1.5.0", "envoi": "unique", "pays": "FR",
    }


def test_withdraw_erases_locally_even_when_unreachable(tmp_path: Path) -> None:
    store = JsonDeclarationStore(tmp_path / "declaration.json")
    assert withdraw(store, _Sender()).was_declared is False
    declare(store, _Sender(), "omega-fold", "1.5.0", key_factory=lambda: KEY)
    sender = _Sender(ok=False)
    result = withdraw(store, sender)
    assert result.was_declared and not result.reception_reached
    assert sender.sent == [{"cle": KEY, "retrait": True}]
    assert store.load() is None


def test_corrupt_store_reads_as_not_declared(tmp_path: Path) -> None:
    path = tmp_path / "declaration.json"
    path.write_text("{pas du json", encoding="utf-8")
    assert JsonDeclarationStore(path).load() is None
    path.write_text(f'{{"cle": "{KEY}", "declare_le": "hier"}}', encoding="utf-8")
    assert JsonDeclarationStore(path).load() is None


SHA = """\
aaa  omega-scan-2.0.0.tar.gz
bbb  omega-scan-2.5.0.tar.gz
ccc  omega-fire-v3.0.tar.gz
ddd  omega-fire-3.5.tar.gz
"""


def test_published_versions_per_software() -> None:
    assert published_versions("omega-scan", SHA) == ["2.5.0", "2.0.0"]
    assert published_versions("omega-fire", SHA) == ["3.5"]
    assert published_versions("omega-check", SHA) == []


def test_update_statuses() -> None:
    newer = compare_with_published("omega-scan", "2.0.0", SHA)
    assert newer.status is UpdateStatus.UPDATE_AVAILABLE and newer.latest == "2.5.0"
    assert newer.archive_url == "https://kraynux.snake-mackarel.ts.net/omega-scan/download/omega-scan-2.5.0.tar.gz"
    assert newer.notes_url.endswith("/omega-scan/download/omega-scan-2.5.0-nouveautes.txt")
    assert compare_with_published("omega-scan", "2.5.0", SHA).status is UpdateStatus.UP_TO_DATE
    assert compare_with_published("omega-scan", "2.6.0", SHA).status is UpdateStatus.AHEAD
    # « 3.5 » publie et installe : a jour (pas « plus recente » a cause d'un .0 manquant).
    assert compare_with_published("omega-fire", "3.5", SHA).status is UpdateStatus.UP_TO_DATE
    assert compare_with_published("omega-fire", "3.5.0", SHA).status is UpdateStatus.UP_TO_DATE
    assert compare_with_published("omega-scan", "2.5.0", None).status is UpdateStatus.UNKNOWN
    assert compare_with_published("omega-scan", "dev", SHA).status is UpdateStatus.UNKNOWN
    assert check_for_update(_Source(SHA), "omega-scan", "2.0.0").latest == "2.5.0"


def test_site_addresses() -> None:
    assert download_base_url("omega-track") == "https://kraynux.snake-mackarel.ts.net/omega-track/download/"
    assert sha_list_url("omega-fire") == "https://kraynux.snake-mackarel.ts.net/omega-fire/download/sha.txt"


def test_project_version_reads_pyproject_then_metadata(tmp_path: Path) -> None:
    from omega_lib.infrastructure.declaration.app_version import project_version

    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "1.6.0"\n', encoding="utf-8")
    assert project_version(tmp_path, "omega-inexistant") == "1.6.0"
    assert project_version(tmp_path / "absent", "omega-inexistant") == "0.0.0"


def test_build_contact_support_puts_the_key_under_var(tmp_path: Path) -> None:
    services = build_contact_support("omega-stress", "1.5.0", tmp_path)
    assert services.software == "omega-stress" and services.version == "1.5.0"
    assert isinstance(services.store, JsonDeclarationStore)
    assert services.store.path == tmp_path / "declaration.json"
    assert not (tmp_path / "declaration.json").exists()  # rien n'est ecrit avant l'accord
