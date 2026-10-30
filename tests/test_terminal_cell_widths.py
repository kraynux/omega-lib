"""Largeur des voyelles devanagari espacantes alignee sur glibc/VTE (plan i18n, hindi)."""
import ctypes
import locale
import unittest

try:  # omega-lib n'a aucune dependance : Rich/Textual viennent du venv de l'outil qui teste
    import rich  # noqa: F401
except ImportError:  # pragma: no cover
    raise unittest.SkipTest("rich absent : test lance depuis le venv d'un outil (omega-serv, omega-fire)")

from rich.cells import cell_len

from omega_lib.i18n.terminal_cell_widths import align_spacing_marks_with_terminal


class TestSpacingMarkWidths(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        align_spacing_marks_with_terminal()

    def test_hindi_measured_like_the_terminal(self):
        # Mesure reelle dans Terminator (VTE) le 2026-10-22 : 5 et 10 colonnes.
        self.assertEqual(cell_len("हिन्दी"), 5)
        self.assertEqual(cell_len("नमस्ते दुनिया"), 10)

    def test_other_scripts_unchanged(self):
        self.assertEqual(cell_len("Français"), 8)
        self.assertEqual(cell_len("Русский"), 7)
        self.assertEqual(cell_len("日志文件"), 8)
        self.assertEqual(cell_len("́"), 0)  # accent combinant (Mn) : toujours 0

    def test_idempotent(self):
        self.assertTrue(align_spacing_marks_with_terminal())
        self.assertEqual(cell_len("हिन्दी"), 5)

    def test_matches_glibc_for_indic_blocks(self):
        try:
            locale.setlocale(locale.LC_CTYPE, "C.UTF-8")
            libc = ctypes.CDLL("libc.so.6")
        except (locale.Error, OSError):
            self.skipTest("glibc indisponible")
        for codepoint in range(0x0900, 0x0D80):
            glibc_width = libc.wcwidth(ctypes.c_wchar(chr(codepoint)))
            if glibc_width >= 0:
                self.assertEqual(cell_len(chr(codepoint)), glibc_width, hex(codepoint))


if __name__ == "__main__":
    unittest.main()
