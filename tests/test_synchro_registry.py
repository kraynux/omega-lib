# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Registre de la zone neutre (etape 3, lot D) : aller-retour et lecture tolerante."""
from __future__ import annotations

import pytest

from omega_lib.synchro.models import ReadStatus
from omega_lib.synchro.registry import (
    CreatedItem,
    CreatedKind,
    LinkedInstallation,
    ZoneRegistry,
    ZoneState,
    registry_from_dict,
    registry_to_dict,
    sheet_copy_name,
    token_copy_name,
)

AT = "2026-11-10T12:00:00Z"
ID = "a" * 32


def _registry() -> ZoneRegistry:
    return ZoneRegistry(
        zone="/var/lib/omega-synchro", state=ZoneState.ACTIVE, updated_at=AT,
        created=(CreatedItem(CreatedKind.GROUP, "omega-synchro", AT),
                 CreatedItem(CreatedKind.DIRECTORY, "/var/lib/omega-synchro", AT),
                 CreatedItem(CreatedKind.MEMBER, "kraynux", AT)),
        installations=(LinkedInstallation(ID, "omega-serv", "omega-serv", "/home/k/omega-serv", "k", "2.6.1", AT,
                                          has_sheet=True),),
    )


def test_round_trip_and_copy_names() -> None:
    registry = _registry()
    result = registry_from_dict(registry_to_dict(registry))
    assert result.ok and result.value == registry
    item = registry.installations[0]
    assert item.token_file == f"jetons/{ID}.json" and item.sheet_file == f"fiches/{ID}.json"
    assert registry.created_items(CreatedKind.MEMBER)[0].target == "kraynux"
    with pytest.raises(ValueError):
        token_copy_name("../../etc/passwd")
    with pytest.raises(ValueError):
        sheet_copy_name("x")


@pytest.mark.parametrize(("change", "status"), [
    ({"schema_version": 2}, ReadStatus.INCOMPATIBLE),
    ({"format": "omega-jeton"}, ReadStatus.INVALID),
    ({"state": "zombie"}, ReadStatus.INVALID),
    ({"zone": "relative/zone"}, ReadStatus.INVALID),
    ({"created": [{"kind": "directory", "target": "/var/../etc", "at": AT}]}, ReadStatus.INVALID),
    ({"created": [{"kind": "member", "target": "root; rm", "at": AT}]}, ReadStatus.INVALID),
    ({"created": [{"kind": "file", "target": "x", "at": AT}]}, ReadStatus.INVALID),
    ({"installations": [{"installation_id": "../x"}]}, ReadStatus.INVALID),
    ({"updated_at": "hier"}, ReadStatus.INVALID),
])
def test_hand_edited_registry_is_refused(change: dict, status: ReadStatus) -> None:
    data = {**registry_to_dict(_registry()), **change}
    assert registry_from_dict(data).status is status


def test_repeated_installation_is_invalid() -> None:
    data = registry_to_dict(_registry())
    data["installations"] = data["installations"] * 2
    assert registry_from_dict(data).status is ReadStatus.INVALID
