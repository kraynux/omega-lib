from omega_lib.terminal.models import RenderProfile
from omega_lib.theme.policies import DEFAULT_TUI_THEME, TUI_THEMES, degrade_to_grayscale
from omega_lib.theme.service import resolve_applied_theme, resolve_palette


def test_all_themes_have_9_color_palette() -> None:
    for definition in TUI_THEMES.values():
        palette = definition.palette
        assert all(
            getattr(palette, field)
            for field in (
                "background", "surface", "panel", "foreground", "accent",
                "secondary", "success", "warning", "error",
            )
        )


def test_resolve_applied_theme_known_name() -> None:
    applied = resolve_applied_theme("omega-dark", RenderProfile.COMPLETE)
    assert applied.theme_name == "omega-dark"
    assert applied.fell_back_from is None


def test_resolve_applied_theme_unknown_name_falls_back() -> None:
    applied = resolve_applied_theme("does-not-exist", RenderProfile.COMPLETE)
    assert applied.theme_name == DEFAULT_TUI_THEME
    assert applied.fell_back_from == "does-not-exist"


def test_resolve_palette_mono_degrades_to_grayscale() -> None:
    palette = resolve_palette("omega-dark", RenderProfile.MONO)
    assert palette.background.startswith("#")
    assert palette.background[1:3] == palette.background[3:5] == palette.background[5:7]


def test_resolve_palette_reduced_flattens_surface_and_panel() -> None:
    palette = resolve_palette("omega-dark", RenderProfile.REDUCED)
    assert palette.surface == palette.background
    assert palette.panel == palette.background


def test_degrade_to_grayscale_leaves_named_colors_unchanged() -> None:
    assert degrade_to_grayscale("cyan") == "cyan"
