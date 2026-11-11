# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Contrats d'interconnexion (D-017, etape 2 du 2026-11-10). Critere de fin de la phase 0 : des fichiers
fabriques a la main (valides, tronques, d'une version future, pieges) sont lus correctement. Aucun test
n'ecrit hors de tmp_path (la zone reelle /var/lib/omega-synchro n'est jamais touchee)."""
from __future__ import annotations

import json
import os
import stat
from datetime import datetime, timezone
from pathlib import Path

import pytest

from omega_lib.infrastructure.synchro.ban_journal import (
    read_active_bans,
    read_ban_journal,
)
from omega_lib.infrastructure.synchro.files import read_contract, write_json_atomic, zone_dir
from omega_lib.infrastructure.synchro.install_token import (
    read_install_token,
    read_machine_fingerprint,
    refresh_install_token,
    token_path,
)
from omega_lib.synchro.codec import (
    active_bans_from_dict,
    active_bans_to_dict,
    ban_event_from_dict,
    ban_event_to_dict,
    sheet_from_dict,
    sheet_to_dict,
    token_from_dict,
    token_to_dict,
)
from omega_lib.synchro.constants import (
    TOKEN_FILE_MODE,
    ZONE_DIR_DEFAULT,
    ZONE_DIR_MODE,
    ZONE_FILE_MODE,
)
from omega_lib.synchro.models import (
    BanAction,
    BanEvent,
    CapabilityState,
    InstanceSheet,
    ReadStatus,
    ServiceInfo,
    SharedFile,
)
from omega_lib.synchro.policies import (
    format_utc,
    is_riposte_origin,
    machine_fingerprint,
    normalize_network,
    parse_utc,
    validate_origin,
)
from omega_lib.synchro.rights import EXPECTED_RIGHTS, expected_right, mode_matches

FIXTURES = Path(__file__).parent / "fixtures" / "synchro"
NOW = datetime(2026, 11, 10, 14, 3, tzinfo=timezone.utc)


# --- Jetons fabriques a la main ------------------------------------------------------------------

@pytest.mark.parametrize(("name", "status"), [
    ("jeton_valide.json", ReadStatus.OK),
    ("jeton_champs_inconnus.json", ReadStatus.OK),
    ("jeton_version_future.json", ReadStatus.INCOMPATIBLE),
    ("jeton_tronque.json", ReadStatus.INVALID),
    ("jeton_chemin_piege.json", ReadStatus.INVALID),
    ("jeton_chemin_relatif.json", ReadStatus.INVALID),
    ("jeton_mauvais_format.json", ReadStatus.INVALID),
    ("jeton_identifiant_invalide.json", ReadStatus.INVALID),
    ("absent.json", ReadStatus.ABSENT),
])
def test_hand_made_tokens(name: str, status: ReadStatus) -> None:
    assert read_contract(FIXTURES / name, token_from_dict).status is status


def test_valid_token_content_and_round_trip() -> None:
    token = read_contract(FIXTURES / "jeton_valide.json", token_from_dict).value
    assert token is not None
    assert token.tool == "omega-serv" and token.contracts["blocklist"] == (1,)
    assert token_from_dict(token_to_dict(token)).value == token


def test_unreadable_token_is_a_state_not_an_error(tmp_path: Path) -> None:
    if os.geteuid() == 0:
        pytest.skip("root lit tout")
    target = tmp_path / "jeton.json"
    target.write_text("{}", encoding="utf-8")
    target.chmod(0)
    assert read_contract(target, token_from_dict).status is ReadStatus.UNREADABLE


def test_non_object_and_huge_files_are_invalid(tmp_path: Path) -> None:
    (tmp_path / "liste.json").write_text("[1, 2]", encoding="utf-8")
    assert read_contract(tmp_path / "liste.json", token_from_dict).status is ReadStatus.INVALID
    (tmp_path / "gros.json").write_bytes(b" " * (1024 * 1024 + 10))
    assert read_contract(tmp_path / "gros.json", token_from_dict).status is ReadStatus.INVALID


# --- Fiches --------------------------------------------------------------------------------------

def test_serv_sheet_unknown_capability_state_and_extra_kept() -> None:
    sheet = read_contract(FIXTURES / "fiche_serv_valide.json", sheet_from_dict).value
    assert sheet is not None
    assert sheet.capabilities["waf"] is CapabilityState.ACTIVE
    assert sheet.capabilities["teleportation"] is CapabilityState.UNKNOWN  # etat futur tolere
    assert sheet.files["blocklist"].contract == ("blocklist", 1)
    assert sheet.extra["exposure"] == "proxy" and sheet.extra["omega_waf"]["mode"] == "block"
    assert sheet.service is not None and sheet.service.unit == "omega-serv-blog.service"


def test_partial_fire_sheet() -> None:
    sheet = read_contract(FIXTURES / "fiche_fire_partielle.json", sheet_from_dict).value
    assert sheet is not None and sheet.partial and sheet.service is None
    assert sheet.capabilities["fail2ban"] is CapabilityState.UNKNOWN


def test_sheet_with_relative_trap_path_is_invalid() -> None:
    assert read_contract(FIXTURES / "fiche_fichier_piege.json", sheet_from_dict).status is ReadStatus.INVALID


def test_sheet_round_trip() -> None:
    sheet = InstanceSheet(
        tool="omega-serv", version="2.6.1", installation_id="9f2c6e1b4a7d4c0e8b3f5a6d7e8c9b0a",
        instance="omega-serv", generated_at=format_utc(NOW),
        capabilities={"waf": CapabilityState.DISABLED},
        service=ServiceInfo("systemd", "omega-serv.service", "omega-serv", "omega-serv", "active"),
        files={"waf-log": SharedFile("/srv/omega-serv/var/log/waf-alerts.log", ("waf-log", 1))},
        extra={"exposure": "direct", "tool": "ignore"},  # une cle du contrat ne peut pas etre ecrasee
    )
    payload = sheet_to_dict(sheet)
    assert payload["tool"] == "omega-serv" and payload["exposure"] == "direct"
    again = sheet_from_dict(json.loads(json.dumps(payload))).value
    assert again is not None and again.files == sheet.files and again.service == sheet.service


# --- Bans ----------------------------------------------------------------------------------------

def test_ban_journal_reads_valid_lines_and_counts_the_rest() -> None:
    result = read_ban_journal(FIXTURES / "bans_journal.jsonl")
    assert result.status is ReadStatus.OK
    assert [e.id[-1] for e in result.events] == ["1", "2", "5"]
    assert result.events[1].network == "198.51.100.4/32"  # IPv4-mapped ramenee en IPv4
    assert result.events[1].expires_at is None  # permanent
    assert result.events[2].action is BanAction.UNBAN
    assert result.invalid_lines == 2  # texte libre + origine reservee
    assert result.incompatible_lines == 1
    # La derniere ligne, en cours d'ecriture, n'est pas consommee.
    size = (FIXTURES / "bans_journal.jsonl").stat().st_size
    assert result.position.offset < size


def test_ban_journal_follows_position_and_detects_rotation(tmp_path: Path) -> None:
    journal = tmp_path / "journal.jsonl"
    event = BanEvent("e1", "2026-11-10T14:07:12Z", BanAction.BAN, "203.0.113.7/32", "omega-fire")
    journal.write_text(json.dumps(ban_event_to_dict(event)) + "\n", encoding="utf-8")
    first = read_ban_journal(journal)
    assert len(first.events) == 1
    with journal.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(ban_event_to_dict(BanEvent(
            "e2", "2026-11-10T14:08:00Z", BanAction.UNBAN, "203.0.113.7", "omega-fire"))) + "\n")
    second = read_ban_journal(journal, first.position)
    assert [e.id for e in second.events] == ["e2"] and not second.restarted
    journal.rename(tmp_path / "journal.jsonl.1")
    journal.write_text("", encoding="utf-8")
    third = read_ban_journal(journal, second.position)
    assert third.restarted and third.events == ()
    assert read_ban_journal(tmp_path / "absent.jsonl").status is ReadStatus.ABSENT


def test_active_bans_snapshot() -> None:
    active = read_active_bans(FIXTURES / "bans_actifs.json").value
    assert active is not None and active.entries[0].origin == "fail2ban:sshd"
    assert active_bans_from_dict(active_bans_to_dict(active)).value == active
    unban_inside = active_bans_to_dict(active)
    unban_inside["entries"][0]["action"] = "unban"
    assert active_bans_from_dict(unban_inside).status is ReadStatus.INVALID


def test_ban_event_validation() -> None:
    good = ban_event_to_dict(BanEvent("e1", "2026-11-10T14:07:12Z", BanAction.BAN, "203.0.113.7/32", "omega-fire"))
    assert ban_event_from_dict(good).ok
    for key, value in (("network", "pas-une-ip"), ("origin", "Omega Fire"), ("at", "hier"),
                       ("action", "kick"), ("expires_at", "bientot")):
        assert ban_event_from_dict(dict(good, **{key: value})).status is ReadStatus.INVALID, key


# --- Regles pures --------------------------------------------------------------------------------

def test_policies() -> None:
    assert format_utc(NOW) == "2026-11-10T14:03:00Z"
    assert parse_utc("2026-11-10T14:03:00Z") == NOW
    assert parse_utc("2026-11-10T14:03:00") is None  # sans fuseau
    assert normalize_network("::ffff:10.0.0.1") == "10.0.0.1/32"
    assert normalize_network("2001:db8::1") == "2001:db8::1/128"
    assert validate_origin("fail2ban:sshd") is None and validate_origin("intervention") is not None
    assert is_riposte_origin("fail2ban:omega-serv-riposte-24h")
    assert is_riposte_origin("fail2ban:x", jail="omega-serv-blog-riposte-1h")
    assert not is_riposte_origin("fail2ban:sshd")
    assert machine_fingerprint("") == "" and len(machine_fingerprint("abc\n")) == 16
    assert machine_fingerprint("abc") != "abc"  # l'identifiant lui-meme n'est jamais publie


def test_zone_dir_override() -> None:
    assert zone_dir({}) == Path(ZONE_DIR_DEFAULT)
    assert zone_dir({"OMEGA_SYNCHRO_DIR": "/tmp/zone"}) == Path("/tmp/zone")


def test_rights_table() -> None:
    zone = expected_right("zone-dirs")
    assert zone.mode == ZONE_DIR_MODE == 0o2750 and zone.owner == "root"
    assert expected_right("zone-bans").mode == ZONE_FILE_MODE == 0o640
    assert mode_matches(0o42750, zone) and not mode_matches(0o2770, zone)
    blocklist = expected_right("serv-blocklist")
    assert mode_matches(0o664, blocklist) and not mode_matches(0o600, blocklist)
    assert expected_right("serv-jail-logs").must_exist
    assert len({right.key for right in EXPECTED_RIGHTS}) == len(EXPECTED_RIGHTS)


# --- Ecriture -------------------------------------------------------------------------------------

def test_atomic_write_sets_mode_explicitly(tmp_path: Path) -> None:
    old = os.umask(0o077)
    try:
        write_json_atomic(tmp_path / "f.json", {"a": 1}, 0o640)
    finally:
        os.umask(old)
    assert stat.S_IMODE((tmp_path / "f.json").stat().st_mode) == 0o640
    assert list(tmp_path.iterdir()) == [tmp_path / "f.json"]  # aucun temporaire laisse


def _refresh(root: Path, version: str = "2.6.1", **kwargs: object):
    return refresh_install_token(root, "omega-serv", version, contracts={"omega-fiche": [1]},
                                 offers=("blocklist",), now=NOW, machine=kwargs.pop("machine", "m1"),  # type: ignore[arg-type]
                                 **kwargs)  # type: ignore[arg-type]


def test_token_created_kept_then_updated(tmp_path: Path) -> None:
    root = tmp_path / "omega-serv"
    root.mkdir()
    created = _refresh(root)
    assert created.outcome == "created" and created.token is not None
    assert stat.S_IMODE(token_path(root).stat().st_mode) == TOKEN_FILE_MODE
    assert _refresh(root).outcome == "unchanged"
    updated = _refresh(root, version="2.6.2")
    assert updated.outcome == "updated" and updated.token is not None
    assert updated.token.installation_id == created.token.installation_id
    assert updated.token.installed_at == created.token.installed_at
    assert read_install_token(root).value == updated.token


def test_token_new_id_on_other_machine(tmp_path: Path) -> None:
    root = tmp_path / "omega-serv"
    root.mkdir()
    first = _refresh(root).token
    moved = _refresh(root, machine="m2")
    assert moved.outcome == "new_id" and moved.token is not None and first is not None
    assert moved.token.installation_id != first.installation_id


def test_token_move_keeps_id_but_copy_gets_new_one(tmp_path: Path) -> None:
    original = tmp_path / "a"
    original.mkdir()
    first = _refresh(original).token
    assert first is not None
    copy = tmp_path / "b"
    (copy / "var").mkdir(parents=True)
    token_path(copy).write_bytes(token_path(original).read_bytes())
    copied = _refresh(copy)
    assert copied.outcome == "new_id"  # l'ancienne racine porte toujours le meme jeton
    moved = tmp_path / "c"
    original.rename(moved)
    relocated = _refresh(moved)
    assert relocated.outcome == "updated" and relocated.token is not None
    assert relocated.token.installation_id == first.installation_id and relocated.token.root == str(moved)


def test_token_never_written_as_root_or_by_another_account(tmp_path: Path) -> None:
    root = tmp_path / "omega-serv"
    root.mkdir()
    assert _refresh(root, euid=0).outcome == "skipped"
    assert _refresh(root, euid=root.stat().st_uid + 1).outcome == "skipped"
    assert not token_path(root).exists()


def test_token_newer_version_is_not_downgraded(tmp_path: Path) -> None:
    root = tmp_path / "omega-serv"
    (root / "var").mkdir(parents=True)
    future = (FIXTURES / "jeton_version_future.json").read_bytes()
    token_path(root).write_bytes(future)
    assert _refresh(root).outcome == "skipped"
    assert token_path(root).read_bytes() == future


def test_broken_token_is_replaced(tmp_path: Path) -> None:
    root = tmp_path / "omega-serv"
    (root / "var").mkdir(parents=True)
    token_path(root).write_text("{cass", encoding="utf-8")
    assert _refresh(root).outcome == "created"


def test_machine_fingerprint_reads_first_available(tmp_path: Path) -> None:
    (tmp_path / "id").write_text("abc\n", encoding="ascii")
    assert read_machine_fingerprint([str(tmp_path / "absent"), str(tmp_path / "id")]) == machine_fingerprint("abc")
    assert read_machine_fingerprint([str(tmp_path / "absent")]) == ""
