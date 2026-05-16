"""T-021: 반도체 특화 사전 1차 검증 (샘플 뉴스 10건).

> "반도체 특화 사전 1차 검증 (샘플 뉴스 10건 테스트) | P1 | 점수 방향성 육안 검증"
>  — Tasks T-021

실행 방법
---------
    python tests/integration/test_phase2_1_lexicon.py

또는::
    python -m unittest tests.integration.test_phase2_1_lexicon -v

검증 목표
---------
1. 호재 키워드가 다수 포함된 기사는 양수 점수.
2. 악재 키워드가 다수 포함된 기사는 음수 점수.
3. 중립 기사는 0 ± 작은 값.
4. 전체 10건 평균이 동일 부호로 분류되어, 사전이 도메인 맥락을 반영함을 확인.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from typing import List, Tuple

# 단독 실행을 위한 sys.path 보정
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# DB 환경변수는 본 검증에서 사용하지 않지만, Settings 빌드를 위해 미리 설정.
os.environ.setdefault("SEMI_SENTI_SQLITE_PATH", str(PROJECT_ROOT / "db" / "semisenti.db"))

from semi_senti.engine import SentimentEngine  # noqa: E402


# ---------------------------------------------------------------------------
# 샘플 뉴스 10건: (label, text)
#   label 의미 → "positive" / "negative" / "neutral"
# ---------------------------------------------------------------------------
SAMPLES: List[Tuple[str, str]] = [
    # 호재 5건
    ("positive",
     "삼성전자가 HBM 신제품 양산을 시작했다. AI 수요 증가에 따른 대형 수주가 이어지며 점유율 확대가 전망된다."),
    ("positive",
     "SK하이닉스는 감산 효과로 가격 인상이 본격화되며 흑자 전환에 성공했다. 데이터센터 향 수요가 신기록을 경신했다."),
    ("positive",
     "글로벌 메모리 업황이 회복 국면에 진입했다. 수율 향상과 함께 영업이익이 사상 최대 수준을 기록할 전망이다."),
    ("positive",
     "HBM 점유율 확대와 AI 수요 폭증으로 호조세가 지속되고 있다. 가격 인상과 흑자 전환이 동시에 진행 중이다."),
    ("positive",
     "감산 정책이 효과를 보이며 공급조정에 성공, 수요 증가와 함께 가격이 반등하고 있다. 신기록 분기 매출이 예상된다."),

    # 악재 4건
    ("negative",
     "공급과잉 우려가 확산되며 재고 누적이 가속화되고 있다. 가격 하락과 수요 둔화로 적자 전환 가능성이 제기된다."),
    ("negative",
     "글로벌 IT 수요 부진으로 메모리 가격이 급락하고 있다. 재고 조정 부담과 수율 저하가 동시에 발생 중이다."),
    ("negative",
     "반도체 업황 불황이 장기화되며 영업이익이 감익 전환했다. 공급과잉 해소가 지연되며 부정적 전망이 우세하다."),
    ("negative",
     "재고 증가와 수요 감소가 겹치며 가격 폭락 우려가 커지고 있다. 적자 전환 리스크 경고가 잇따른다."),

    # 중립 1건
    ("neutral",
     "정부는 반도체 산업의 R&D 세제 혜택 방안을 검토 중이다. 업계와 협의 후 연내 발표 예정이다."),
]


class TestLexiconDirectionality(unittest.TestCase):
    """샘플 뉴스 10건에 대해 점수의 부호 일관성을 검증."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = SentimentEngine()
        cls.results = []
        for label, text in SAMPLES:
            res = cls.engine.analyze_text(text)
            cls.results.append((label, text, res))

    def test_positive_samples_score_positive(self) -> None:
        for label, text, res in self.results:
            if label == "positive":
                with self.subTest(text=text[:30] + "..."):
                    self.assertGreater(
                        res.score, 0,
                        msg=f"호재 기사인데 점수 {res.score:.2f} (raw={res.raw_score:.2f})",
                    )

    def test_negative_samples_score_negative(self) -> None:
        for label, text, res in self.results:
            if label == "negative":
                with self.subTest(text=text[:30] + "..."):
                    self.assertLess(
                        res.score, 0,
                        msg=f"악재 기사인데 점수 {res.score:.2f} (raw={res.raw_score:.2f})",
                    )

    def test_neutral_sample_score_small(self) -> None:
        for label, text, res in self.results:
            if label == "neutral":
                with self.subTest(text=text[:30] + "..."):
                    self.assertLessEqual(
                        abs(res.score), 30.0,
                        msg=f"중립 기사인데 점수 {res.score:.2f}",
                    )

    def test_aggregate_distribution(self) -> None:
        """positive 평균 > negative 평균이 명확하게 성립해야 함."""
        pos_avg = sum(r.score for l, _, r in self.results if l == "positive") / 5
        neg_avg = sum(r.score for l, _, r in self.results if l == "negative") / 4
        self.assertGreater(pos_avg, neg_avg + 50,
                           msg=f"positive 평균 {pos_avg:.2f} <= negative 평균 {neg_avg:.2f}+50")

    def test_print_report(self) -> None:
        """육안 검증용 리포트 출력 (실패 없이 항상 통과)."""
        print()
        print("=" * 80)
        print(" Semi Senti - 반도체 특화 사전 1차 검증 (T-021)")
        print("=" * 80)
        print(f" 토크나이저: {self.engine.tokenizer.tagger_name}")
        print(f" 사전 단어수: {len(self.engine.lexicon)}")
        print("-" * 80)
        for i, (label, text, res) in enumerate(self.results, start=1):
            tag = {"positive": "[+]", "negative": "[-]", "neutral": "[ ]"}[label]
            top = ", ".join(
                f"{h['word']}({h['contribution']:+.1f})"
                for h in res.top_keywords[:3]
            )
            print(
                f" {i:2d} {tag} score={res.score:+6.2f} raw={res.raw_score:+6.1f} | "
                f"top={top or '∅'}"
            )
            print(f"      {text[:70]}{'...' if len(text) > 70 else ''}")
        print("=" * 80)


if __name__ == "__main__":
    unittest.main(verbosity=2)
