"""반도체 특화 감성 사전 (T-017).

> "도메인 고유 해석 예시: 감산 → 호재(양수 가중치), 재고 문맥 → 악재(음수 가중치)"
>  — PRD §F-2.2 처리 파이프라인 (L162)

설계 원칙
---------
1. **도메인 우선**: 일반 감성 사전과 달리, 반도체 산업 맥락에서의 해석을 따른다.
   - "감산" : 생산 조정 → 공급 과잉 해소 신호 → **호재 (+)**
   - "재고" : 재고 누적 → 공급 과잉 → **악재 (-)**
2. **가중치는 절대값 1~6 범위로 보정**. 큰 절대값일수록 강한 신호.
3. **단어/구문 모두 지원**: 형태소 추출이 실패한 경우를 대비해 본문 부분 일치도 허용.
4. **확장 용이**: 외부에서 ``override(extra)`` 로 사전 갱신 가능 (운영 중 튜닝).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 기본 사전 (Phase 2-1 초안 - T-021 검증 후 조정 예정)
# ---------------------------------------------------------------------------
# 호재 키워드 (양수 가중치)
_POSITIVE: Dict[str, float] = {
    # 강한 호재 (+4 ~ +6)
    "HBM": 5.0,
    "고대역폭메모리": 5.0,
    "감산": 4.5,           # 공급조절 → 가격 회복 신호
    "수요": 4.0,
    "수요증가": 5.0,
    "수율": 4.0,           # 수율 향상 맥락. 부정 동시 등장 시 가중치 상쇄됨.
    "수율향상": 5.5,
    "회복": 4.5,
    "반등": 4.0,
    "흑자": 5.0,
    "흑자전환": 6.0,
    "최대": 4.0,
    "신기록": 5.0,
    "역대급": 4.5,
    "가격인상": 4.0,
    "점유율": 3.5,
    "점유율확대": 5.0,
    "대형수주": 5.5,
    "양산": 3.5,
    "초도양산": 4.5,
    "공급계약": 4.0,
    "독점": 4.0,
    "AI": 3.0,
    "AI수요": 5.0,
    "데이터센터": 3.5,
    "혁신": 3.0,
    # 일반 호재 (+1 ~ +3)
    "성장": 3.0,
    "확대": 2.5,
    "증가": 2.5,
    "상승": 2.5,
    "호조": 3.0,
    "개선": 2.5,
    "긍정적": 2.0,
    "낙관": 2.5,
    "투자": 2.0,
    "신제품": 2.5,
}

# 악재 키워드 (음수 가중치)
_NEGATIVE: Dict[str, float] = {
    # 강한 악재 (-4 ~ -6)
    "공급과잉": -5.5,
    "재고조정": -5.0,
    "재고증가": -5.0,
    "재고누적": -5.5,
    "수요둔화": -5.0,
    "수요부진": -5.5,
    "수요감소": -5.5,
    "가격하락": -5.0,
    "가격급락": -6.0,
    "급락": -5.5,
    "폭락": -6.0,
    "적자": -5.5,
    "적자전환": -6.0,
    "감익": -5.0,
    "수율저하": -5.5,
    "불량률": -5.0,
    "불황": -5.0,
    "리세션": -5.0,
    "둔화": -3.5,
    # 일반 악재 (-1 ~ -3)
    "감소": -2.5,
    "하락": -2.5,
    "부진": -3.0,
    "악화": -3.0,
    "위축": -3.0,
    "지연": -2.0,
    "리스크": -2.5,
    "우려": -2.5,
    "경고": -3.0,
    "부정적": -2.5,
    "비관": -3.0,
    # "재고" 단독: 보통 악재 문맥 (PRD 직접 인용)
    "재고": -3.5,
}


@dataclass
class KeywordHit:
    """매칭된 키워드 한 건의 정보."""

    word: str
    weight: float
    count: int = 1

    @property
    def contribution(self) -> float:
        """가중치 × 등장 빈도."""
        return self.weight * self.count


@dataclass
class SemiconductorLexicon:
    """반도체 도메인 감성 사전.

    Parameters
    ----------
    positive:
        호재 키워드 dict. 기본값 ``_POSITIVE``.
    negative:
        악재 키워드 dict. 기본값 ``_NEGATIVE``.

    Notes
    -----
    내부적으로는 ``_terms`` (word → weight) 단일 dict 로 합쳐 사용한다.
    조회 시 대소문자/공백을 정규화하여 매칭 안정성을 높인다.
    """

    positive: Mapping[str, float] = field(default_factory=lambda: dict(_POSITIVE))
    negative: Mapping[str, float] = field(default_factory=lambda: dict(_NEGATIVE))

    def __post_init__(self) -> None:
        merged: Dict[str, float] = {}
        for word, w in self.positive.items():
            merged[self._normalize(word)] = float(w)
        for word, w in self.negative.items():
            merged[self._normalize(word)] = float(w)
        self._terms: Dict[str, float] = merged

    # ------------------------------------------------------------------ utils
    @staticmethod
    def _normalize(word: str) -> str:
        if word is None:
            return ""
        return word.strip().replace(" ", "").lower()

    # ------------------------------------------------------------------ public
    def __len__(self) -> int:
        return len(self._terms)

    def __contains__(self, word: str) -> bool:
        return self._normalize(word) in self._terms

    def weight_of(self, word: str) -> Optional[float]:
        return self._terms.get(self._normalize(word))

    def override(self, extra: Mapping[str, float]) -> None:
        """외부 dict 로 사전을 갱신 (운영 중 튜닝)."""
        for w, weight in extra.items():
            self._terms[self._normalize(w)] = float(weight)
        _LOGGER.info("Lexicon override: +%d terms", len(extra))

    def all_terms(self) -> Dict[str, float]:
        """현재 사전의 단어→가중치 dict 복사본."""
        return dict(self._terms)

    # ------------------------------------------------------------------ matching
    def match_tokens(self, tokens: Iterable[str]) -> List[KeywordHit]:
        """형태소 토큰 리스트와 사전을 매칭하여 ``KeywordHit`` 리스트 반환.

        동일 단어가 여러 번 등장하면 ``count`` 가 누적된다.
        """
        counter: Dict[str, int] = {}
        for tok in tokens or []:
            key = self._normalize(tok)
            if key and key in self._terms:
                counter[key] = counter.get(key, 0) + 1

        return [
            KeywordHit(word=key, weight=self._terms[key], count=cnt)
            for key, cnt in counter.items()
        ]

    def match_text(self, text: str) -> List[KeywordHit]:
        """단순 부분 문자열 매칭 (형태소 분석이 실패한 경우의 폴백).

        KoNLPy 없이도 최소한의 도메인 신호 감지가 가능하도록 한다.
        성능보다는 가용성을 우선한다.
        """
        if not text:
            return []
        normalized_text = text.replace(" ", "").lower()
        hits: List[KeywordHit] = []
        for term, weight in self._terms.items():
            if not term:
                continue
            cnt = normalized_text.count(term)
            if cnt > 0:
                hits.append(KeywordHit(word=term, weight=weight, count=cnt))
        return hits


def build_default_lexicon() -> SemiconductorLexicon:
    """기본 사전 팩토리. ``SentimentEngine`` 에서 사용."""
    return SemiconductorLexicon()
