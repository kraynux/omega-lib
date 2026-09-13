from omega_lib.terminal.models import RenderProfile, TerminalSignals
from omega_lib.terminal.service import resolve_render_profile


def test_known_family_gets_its_profile() -> None:
    profile = resolve_render_profile(TerminalSignals(family="kitty", columns=200, rows=50))
    assert profile.render_profile == RenderProfile.COMPLETE


def test_unknown_family_falls_back_to_default() -> None:
    profile = resolve_render_profile(TerminalSignals(family="does-not-exist", columns=200, rows=50))
    assert profile.render_profile == RenderProfile.REDUCED


def test_small_terminal_degrades_even_a_capable_family() -> None:
    profile = resolve_render_profile(TerminalSignals(family="kitty", columns=70, rows=20))
    assert profile.render_profile == RenderProfile.MONO


def test_ssh_legacy_is_mono() -> None:
    profile = resolve_render_profile(TerminalSignals(family="ssh-legacy", columns=200, rows=50))
    assert profile.render_profile == RenderProfile.MONO
