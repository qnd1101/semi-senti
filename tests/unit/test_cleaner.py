"""``TextCleaner`` 단위 테스트 (T-012)."""

from __future__ import annotations

import unittest

from semi_senti.collector.cleaner import TextCleaner


class TestTextCleaner(unittest.TestCase):
    def setUp(self) -> None:
        self.cleaner = TextCleaner()

    def test_none_and_empty(self) -> None:
        self.assertEqual(self.cleaner.clean(None), "")
        self.assertEqual(self.cleaner.clean(""), "")
        self.assertEqual(self.cleaner.clean("   "), "")

    def test_strip_bold_and_entities(self) -> None:
        raw = '<b>HBM</b> 수요 &quot;역대급&quot;... 공급 부족'
        cleaned = self.cleaner.clean(raw)
        self.assertNotIn("<b>", cleaned)
        self.assertNotIn("&quot;", cleaned)
        self.assertIn('"역대급"', cleaned)
        self.assertIn("HBM 수요", cleaned)

    def test_collapses_whitespace_and_newlines(self) -> None:
        raw = "감산\n\n\t\t공급과잉      해소"
        cleaned = self.cleaner.clean(raw)
        self.assertEqual(cleaned, "감산 공급과잉 해소")

    def test_removes_control_chars(self) -> None:
        raw = "정상\x00\x01\x02 텍스트"
        cleaned = self.cleaner.clean(raw)
        self.assertEqual(cleaned, "정상 텍스트")

    def test_strip_script_style_tags(self) -> None:
        raw = "<script>alert(1)</script>본문<style>.x{}</style>끝"
        cleaned = self.cleaner.clean(raw)
        self.assertNotIn("alert", cleaned)
        self.assertNotIn(".x", cleaned)
        self.assertIn("본문", cleaned)
        self.assertIn("끝", cleaned)


if __name__ == "__main__":
    unittest.main(verbosity=2)
