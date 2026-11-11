# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
from omega_lib.synchro.registry import (
    CreatedItem,
    CreatedKind,
    ZoneRegistry,
    ZoneState,
    registry_from_dict,
    registry_to_dict,
)
from omega_lib.synchro.service_group import (
    drop_in_directory,
    drop_in_path,
    drop_in_text,
    grants_zone_group,
    service_name,
)


def test_drop_in_paths():
    assert drop_in_directory("omega-serv") == "/etc/systemd/system/omega-serv.service.d"
    assert drop_in_path("omega-serv.service", "/tmp/x/") == "/tmp/x/omega-serv.service.d/omega-synchro.conf"
    assert service_name("omega-serv-blog.service") == "omega-serv-blog"


def test_drop_in_text_grants_the_zone_group():
    assert grants_zone_group(drop_in_text())
    assert not grants_zone_group("[Unit]\nSupplementaryGroups=omega-synchro\n")
    assert not grants_zone_group("[Service]\nSupplementaryGroups=omega-synchronisation\n")
    assert grants_zone_group("[Service]\nSupplementaryGroups=adm omega-synchro\n")


def test_registry_keeps_service_group_items():
    registry = ZoneRegistry("/var/lib/omega-synchro", ZoneState.ACTIVE, "2026-11-10T10:00:00Z",
                            (CreatedItem(CreatedKind.SERVICE_GROUP, "omega-serv", "2026-11-10T10:00:00Z"),))
    result = registry_from_dict(registry_to_dict(registry))
    assert result.value == registry
    data = registry_to_dict(registry)
    data["created"][0]["target"] = "../etc"
    assert registry_from_dict(data).value is None
