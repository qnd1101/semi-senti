"""SentimentEngine (T-015, T-018, T-019, T-020).

> "Raw Score = Σ(매칭 키워드 가중치) ... 정규화 → -100 ~ +100 ... 일자별·종목별
>  감성 지수를 SQLite 에 기록" — PRD §F-2.1 / F-2.2

처리 파이프라인
---------------
1. **Tokenize**     : ``KoreanTokenizer`` 로 명사/형용사 추출 (T-016)
2. **Match**        : ``SemiconductorLexicon`` 과 가중치 매칭 (T-017, T-018)
3. **Aggregate**    : ``raw_score = Σ(weight × count)`` (T-018)
4. **Normalize**    : ``score = 100 × tanh(raw_score / k)`` (T-019)
5. **Persist**      : ``sentiment_scores`` 테이블에 일자별·종목별 UPSERT (T-020)
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional

from ..config import Settings, get_settings
from ..db import DBControl
from .lexicon import KeywordHit, SemiconductorLexicon, build_default_lexicon
from .tokenizer import KoreanTokenizer

_LOGGER = logging.getLogger(__name__)


@dataclass
class SentimentResult:
    """단일 문서 또는 집계 결과."""

    score: float                         # -100 ~ +100
    raw_score: float                     # 정규화 전 합산값
    hits: List[KeywordHit] = field(default_factory=list)
    news_count: int = 0

    @property
    def top_keywords(self) -> List[Dict[str, Any]]:
        """contribution 절대값 기준 상위 키워드 dict 리스트."""
        sorted_hits = sorted(self.hits, key=lambda h: abs(h.contribution), reverse=True)
        return [
            {"word": h.word, "weight": h.weight, "count": h.count, "contribution": h.contribution}
            for h in sorted_hits
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "raw_score": self.raw_score,
            "news_count": self.news_count,
            "top_keywords": self.top_keywords,
        }


class SentimentEngine:
    """반도체 특화 감성 분석 엔진."""

    def __init__(
        self,
        db: Optional[DBControl] = None,
        *,
        tokenizer: Optional[KoreanTokenizer] = None,
        lexicon: Optional[SemiconductorLexicon] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._tokenizer = tokenizer or KoreanTokenizer(settings=self._settings)
        self._lexicon = lexicon or build_default_lexicon()
        self._db: Optional[DBControl] = db
        self._owns_db: bool = db is None

    # ------------------------------------------------------------------ life
    def db(self) -> DBControl:
        if self._db is None:
            self._db = DBControl(db_path=self._settings.sqlite_path)
            self._db.connect()
        else:
            self._db.connect()
        return self._db

    def close(self) -> None:
        if self._owns_db and self._db is not None:
            self._db.close()
            self._db = None

    def __enter__(self) -> "SentimentEngine":
        self.db()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ------------------------------------------------------------------ properties
    @property
    def lexicon(self) -> SemiconductorLexicon:
        return self._lexicon

    @property
    def tokenizer(self) -> KoreanTokenizer:
        return self._tokenizer

    # ------------------------------------------------------------------ scoring (T-018, T-019)
    def analyze_text(self, text: str) -> SentimentResult:
        """단일 문서를 분석해 ``SentimentResult`` 반환.

        - 빈 입력은 ``score=0, raw_score=0`` 으로 반환 (중립).
        - 형태소 분석 후 사전 매칭 → 매칭이 0건이면 본문 부분 매칭으로 보강.
        """
        if not text or not text.strip():
            return SentimentResult(score=0.0, raw_score=0.0, news_count=0)

        tokens = self._tokenizer.extract_keywords(text)
        hits = self._lexicon.match_tokens(tokens)
        if not hits:
            # 형태소 매칭 실패 시 부분 매칭으로 폴백 (도메인 신호 누락 방지).
            hits = self._lexicon.match_text(text)

        raw_score = float(sum(h.contribution for h in hits))
        score = self.normalize(raw_score)
        return SentimentResult(score=score, raw_score=raw_score, hits=hits, news_count=1)

    def normalize(self, raw_score: float) -> float:
        """raw_score → -100 ~ +100 (T-019).

        ``score = 100 × tanh(raw_score / k)``

        - k 가 작을수록 작은 raw 도 빠르게 ±100 에 근접 (민감).
        - k 가 클수록 완만 (둔감).
        - tanh 는 합산 가중치가 무경계인 환경에서 안전한 압축 함수.
        """
        k = max(1.0, float(self._settings.sentiment_normalization_k))
        try:
            score = 100.0 * math.tanh(float(raw_score) / k)
        except (OverflowError, ValueError) as exc:
            _LOGGER.warning("정규화 실패(%s) → 0 으로 폴백: raw=%s", exc, raw_score)
            return 0.0
        # 안전망: 부동소수 오차로 ±100.0001 등이 나오는 경우 클램프.
        return max(-100.0, min(100.0, score))

    # ------------------------------------------------------------------ batch
    def analyze_news_rows(self, news_rows: Iterable[Mapping[str, Any]]) -> SentimentResult:
        """여러 뉴스 row 를 일괄 분석해 단일 집계 결과를 반환.

        ``news`` 테이블 행을 받아 ``title + cleaned_text`` 를 합쳐 분석한다.
        """
        merged_hits: Dict[str, KeywordHit] = {}
        total_raw = 0.0
        count = 0
        for row in news_rows or []:
            text = " ".join(
                str(row.get(k) or "") for k in ("title", "summary", "cleaned_text")
            )
            sub = self.analyze_text(text)
            if sub.news_count == 0:
                continue
            count += 1
            total_raw += sub.raw_score
            for h in sub.hits:
                existing = merged_hits.get(h.word)
                if existing is None:
                    merged_hits[h.word] = KeywordHit(
                        word=h.word, weight=h.weight, count=h.count
                    )
                else:
                    existing.count += h.count
        return SentimentResult(
            score=self.normalize(total_raw),
            raw_score=total_raw,
            hits=list(merged_hits.values()),
            news_count=count,
        )

    # ------------------------------------------------------------------ DB persistence (T-020)
    def score_news_and_store(self, stock_code: str, score_date: str) -> SentimentResult:
        """주어진 (stock_code, date) 의 뉴스를 일괄 분석 → ``sentiment_scores`` UPSERT.

        - ``news.sentiment_score`` 컬럼도 개별 row 별로 갱신한다.
        - 해당 일자에 뉴스가 없으면 score=0, news_count=0 으로 적재.
        """
        if not stock_code or not score_date:
            raise ValueError("stock_code/score_date 는 필수입니다.")

        db = self.db()
        rows = db.fetch_all(
            "SELECT id, title, summary, cleaned_text FROM news "
            "WHERE stock_code = ? AND substr(published_at, 1, 10) = ?",
            (stock_code, score_date),
        )

        # 1) 개별 뉴스 score 갱신 (Phase 3 대시보드/Phase 4 알림에서 활용).
        for row in rows:
            text = " ".join(str(row.get(k) or "") for k in ("title", "summary", "cleaned_text"))
            sub = self.analyze_text(text)
            db.update(
                "news",
                {
                    "sentiment_score": sub.score,
                    "sentiment_raw_score": sub.raw_score,
                },
                where="id = ?",
                where_params=(row["id"],),
            )

        # 2) 일자별 집계 → sentiment_scores 테이블.
        aggregated = self.analyze_news_rows(rows)
        top_kws = aggregated.top_keywords[: self._settings.sentiment_top_keyword_limit]

        db.upsert(
            "sentiment_scores",
            {
                "stock_code": stock_code,
                "score_date": score_date,
                "score": aggregated.score,
                "raw_score": aggregated.raw_score,
                "news_count": aggregated.news_count,
                "top_keywords": json.dumps(top_kws, ensure_ascii=False),
                "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            },
            conflict_columns=["stock_code", "score_date"],
            update_columns=["score", "raw_score", "news_count", "top_keywords", "updated_at"],
        )
        _LOGGER.info(
            "감성 적재: stock=%s date=%s score=%.2f raw=%.2f news=%d",
            stock_code, score_date, aggregated.score, aggregated.raw_score, aggregated.news_count,
        )
        return aggregated

    def get_latest_score(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """``sentiment_scores`` 의 최신 1건을 dict 로 반환."""
        return self.db().fetch_one(
            "SELECT score_date, score, raw_score, news_count, top_keywords "
            "FROM sentiment_scores WHERE stock_code = ? "
            "ORDER BY score_date DESC LIMIT 1",
            (stock_code,),
        )
