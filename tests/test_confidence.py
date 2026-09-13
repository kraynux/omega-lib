from omega_lib.core.confidence import ConfidenceLevel, confidence_strength


def test_all_members_have_distinct_ascii_values() -> None:
    values = [member.value for member in ConfidenceLevel]
    assert values == ["verified", "declared", "corroborated", "inferred", "unknown"]


def test_strength_ordering() -> None:
    ordered = sorted(ConfidenceLevel, key=confidence_strength, reverse=True)
    assert ordered == [
        ConfidenceLevel.VERIFIED,
        ConfidenceLevel.CORROBORATED,
        ConfidenceLevel.DECLARED,
        ConfidenceLevel.INFERRED,
        ConfidenceLevel.UNKNOWN,
    ]
