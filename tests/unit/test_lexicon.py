"""``SemiconductorLexicon`` 단위 테스트 (T-017)."""

from __future__ import annotations

import unittest

from semi_senti.engine.lexicon import SemiconductorLexicon, build_default_lexicon


class TestSemiconductorLexicon(unittest.TestCase):
    def setUp(self) -> None:
        self.lex = build_default_lexicon()

    def test_domain_specific_signs(self) -> None:
        # PRD §F-2.2: 감산 → 호재(+), 재고 → 악재(-).
        self.assertGreater(self.lex.weight_of("감산") or 0, 0)
        self.assertLess(self.lex.weight_of("재고") or 0, 0)
        self.assertGreater(self.lex.weight_of("HBM") or 0, 0)
        self.assertLess(self.lex.weight_of("공급과잉") or 0, 0)

    def test_normalization_is_case_and_space_insensitive(self) -> None:
        self.assertIn("hbm", self.lex)         # 소문자
        self.assertIn("H B M", self.lex)        # 공백 포함
        self.assertEqual(self.lex.weight_of("HBM"), self.lex.weight_of("hbm"))

    def test_match_tokens_accumulates_count(self) -> None:
        hits = self.lex.match_tokens(["HBM", "수요", "HBM", "기타단어"])
        word_count = {h.word: h.count for h in hits}
        self.assertEqual(word_count.get("hbm"), 2)
        self.assertEqual(word_count.get("수요"), 1)
        self.assertNotIn("기타단어", word_count)

    def test_match_text_partial(self) -> None:
        text = "수요 증가 + 가격 인상 + 재고 누적"
        hits = self.lex.match_text(text)
        words = {h.word for h in hits}
        self.assertTrue({"수요", "가격인상"}.issubset(words))
        # "재고누적" 자체가 사전에 있어야 매칭됨.
        self.assertIn("재고누적", words)

    def test_override(self) -> None:
        self.lex.override({"양자컴퓨팅": 7.0})
        self.assertEqual(self.lex.weight_of("양자컴퓨팅"), 7.0)

    def test_keyword_hit_contribution(self) -> None:
        hits = self.lex.match_tokens(["감산", "감산", "감산"])
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].count, 3)
        self.assertAlmostEqual(hits[0].contribution, hits[0].weight * 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
