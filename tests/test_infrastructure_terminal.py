from omega_lib.infrastructure.terminal.detector import SystemTerminalDetector
from omega_lib.infrastructure.terminal.fallback_resolver import resolve_family
from omega_lib.infrastructure.terminal.raw_capabilities import RawTerminalSignals


def _signals(**overrides: object) -> RawTerminalSignals:
    defaults: dict[str, object] = {
        "term": "", "term_program": "", "colorterm": "", "is_ssh": False,
        "columns": 200, "rows": 50, "has_terminator_marker": False,
        "has_konsole_marker": False, "has_gnome_terminal_marker": False,
    }
    defaults.update(overrides)
    return RawTerminalSignals(**defaults)  # type: ignore[arg-type]


def test_resolve_family_from_term_program() -> None:
    assert resolve_family(_signals(term_program="ghostty")) == "ghostty"


def test_resolve_family_ssh_modern() -> None:
    assert resolve_family(_signals(is_ssh=True, colorterm="truecolor")) == "ssh-modern"


def test_resolve_family_ssh_legacy() -> None:
    assert resolve_family(_signals(is_ssh=True)) == "ssh-legacy"


def test_resolve_family_konsole_marker_overrides_term() -> None:
    assert resolve_family(_signals(term="xterm-256color", has_konsole_marker=True)) == "konsole"


def test_resolve_family_unknown_returns_raw_term() -> None:
    assert resolve_family(_signals(term="something-obscure")) == "something-obscure"


def test_system_terminal_detector_returns_real_signals() -> None:
    signals = SystemTerminalDetector().detect()
    assert signals.columns > 0
    assert signals.rows > 0
