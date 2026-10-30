"""Ordre visuel droite-a-gauche fait par le programme dans la TUI (omega-serv, plan i18n lot 11, option C ; partage via omega-lib)."""
import unittest

try:  # omega-lib n'a aucune dependance : Rich/Textual viennent du venv de l'outil qui teste
    import rich  # noqa: F401
except ImportError:  # pragma: no cover
    raise unittest.SkipTest("rich absent : test lance depuis le venv d'un outil (omega-serv, omega-fire)")

from rich.cells import cell_len
from rich.segment import Segment
from rich.style import Style

from omega_lib.i18n.terminal_bidi import install_visual_reordering, visual_order

LRI, PDI, LRM = chr(0x2066), chr(0x2069), chr(0x200E)


class TestVisualOrder(unittest.TestCase):
    def test_text_without_rtl_letters_is_untouched(self):
        for text in ("Service", "Registre (12)", "  centré  ", "日志文件", "हिन्दी", ""):
            self.assertIs(visual_order(text), text)

    def test_arabic_label_is_reversed_and_margins_stay_in_place(self):
        # Libelle de bouton centre : les marges ne bougent jamais (rien ne sort de la case).
        self.assertEqual(visual_order("  الخدمة    "), "  ةمدخلا    ")
        self.assertEqual(visual_order("سجل القدرات"), "تاردقلا لجس")

    def test_width_never_changes(self):
        for text in ("  الخدمة    ", "الخطوة 4/8: التهيئة الأساسية", "هِندي مُشكَّل", "مسار: /var/www/html"):
            self.assertEqual(cell_len(visual_order(text)), cell_len(text))

    def test_numbers_and_latin_words_keep_their_reading_order(self):
        self.assertEqual(visual_order("الخطوة 4/8: التهيئة الأساسية"), "ةيساسألا ةئيهتلا :4/8 ةوطخلا")
        self.assertEqual(visual_order("WAF - الوحدات"), "WAF - تادحولا")

    def test_paths_stay_in_one_piece(self):
        self.assertEqual(visual_order("مسار: /var/www/html"), "/var/www/html :راسم")
        self.assertEqual(
            visual_order("لم يُعثر على أي حزمة تحت secure/waf/rules/."),
            ".secure/waf/rules/ تحت ةمزح يأ ىلع رثعيُ مل",
        )

    def test_isolated_date_is_kept_whole_and_controls_are_dropped(self):
        text = f"أُنشئ في {LRI}2026-10-23 01:22{PDI} · 12 قدرة"
        self.assertEqual(visual_order(text), "ةردق 12 · 2026-10-23 01:22 يف ئشنأُ")
        self.assertNotIn(LRM, visual_order(f"{LRM}الخدمة{LRM}"))

    def test_brackets_are_mirrored(self):
        self.assertEqual(visual_order("حذف الإدخال (نعم/لا)"), "(ال/معن) لاخدإلا فذح")

    def test_vowel_marks_stay_on_their_letter(self):
        self.assertEqual(visual_order("هِند"), "دنهِ")


class TestTextualHook(unittest.TestCase):
    def test_strip_is_ordered_per_style_run(self):
        from textual.strip import Strip

        from omega_lib.i18n.terminal_bidi import visual_strip

        same, border = Style(bold=True), Style(italic=True)
        strip = Strip([Segment("سجل ", same), Segment("القدرات", same), Segment("│", border), Segment("الخدمة", same)])
        ordered = visual_strip(strip)
        self.assertEqual([segment.text for segment in ordered], ["تاردقلا لجس", "│", "ةمدخلا"])
        self.assertEqual(ordered.cell_length, strip.cell_length)

    def test_strip_without_rtl_text_is_returned_as_is(self):
        from textual.strip import Strip

        from omega_lib.i18n.terminal_bidi import visual_strip

        strip = Strip([Segment("Service", Style(bold=True))])
        self.assertIs(visual_strip(strip), strip)

    def test_install_hooks_widget_line_rendering(self):
        from textual._styles_cache import StylesCache

        from omega_lib.i18n import terminal_bidi

        original = StylesCache.__dict__["render_line"]
        self.addCleanup(setattr, terminal_bidi, "_installed", False)
        self.addCleanup(setattr, StylesCache, "render_line", original)
        self.assertTrue(install_visual_reordering())
        self.assertTrue(install_visual_reordering())  # idempotent
        self.assertIsNot(StylesCache.__dict__["render_line"], original)


if __name__ == "__main__":
    unittest.main()
