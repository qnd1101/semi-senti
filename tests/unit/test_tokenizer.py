"""``KoreanTokenizer`` 단위 테스트 (T-014, T-016).

KoNLPy 미설치 환경에서도 동작해야 한다 (폴백 모드 검증).
"""

from __future__ import annotations

import unittest

from semi_senti.engine.tokenizer import KoreanTokenizer


class TestKoreanTokenizer(unittest.TestCase):
    def test_extract_keywords_returns_list(self) -> None:
        tok = KoreanTokenizer()
        result = tok.extract_keywords("HBM 수요 폭증")
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) >= 1)

    def test_empty_inputs(self) -> None:
        tok = KoreanTokenizer()
        self.assertEqual(tok.extract_keywords(""), [])
        self.assertEqual(tok.extract_keywords("   "), [])
        self.assertEqual(tok.extract_keywords(None), [])  # type: ignore[arg-type]

    def test_fallback_mode_extracts_hangul_and_english(self) -> None:
        """폴백(정규식) 토크나이저가 활성화된 경우 한글/영문 모두 잡아야 함."""
        tok = KoreanTokenizer()
        # 폴백 모드일 때만 의미 있는 검증
        if not tok.is_fallback:
            self.skipTest("KoNLPy 가 설치되어 있어 폴백 분기 검증 생략")
        result = tok.extract_keywords("HBM 수요 폭증")
        self.assertIn("HBM", result)
        self.assertIn("수요", result)

    def test_extract_keywords_many(self) -> None:
        tok = KoreanTokenizer()
        out = tok.extract_keywords_many(["감산 효과", "공급과잉 우려"])
        self.assertEqual(len(out), 2)
        self.assertIsInstance(out[0], list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
