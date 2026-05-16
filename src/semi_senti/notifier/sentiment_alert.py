"""감성 점수 ±30pt 급변 경고 워처 (T-042, F-5.1.2).

> "감성 점수가 설정된 임계값을 급격히 초과(예: ±30pt 이상 급변)한 경우,
>  NotificationManager 가 경고 알림을 발송한다."

본 모듈은 ``sentiment_scores`` 테이블의 시계열을 비교하여 임계값을
초과한 변동만 ``NotificationManager.notify_sentiment_shift`` 로 흘려보낸다.

주의
----
- 이 워처는 *상태가 없는* 단발성 평가만 수행한다. 폴링/스케줄링은
  CLI(`watch sentiment`) 또는 외부 cron 에서 담당한다.
- 동일 변동을 반복 발송하지 않도록 ``NotificationManager`` 의 dedupe 로직을
  믿고, 본 모듈에서는 `previous_record_date != current_record_date` 인
  경우만 발송 대상으로 본다.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from ..config import Settings, get_settings
from ..db import DBControl
from .manager import NotificationManager, NotificationResult

_LOGGER = logging.getLogger(__name__)


class SentimentAlertWatcher:
    """감성 점수 급변 감시 + 알림 트리거.

    Parameters
    ----------
    threshold_pt:
        |Δ| >= threshold_pt 일 때 알림. 기본 30pt (PRD 예시값).
    db / manager:
        외부 주입 우선. 미지정 시 본 클래스가 생성.
    """

    def __init__(
        self,
        *,
        threshold_pt: Optional[float] = None,
        db: Optional[DBControl] = None,
        manager: Optional[NotificationManager] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._settings = settings or get_settings()
        threshold_value = (
            threshold_pt if threshold_pt is not None else self._settings.sentiment_shift_threshold_pt
        )
        if threshold_value <= 0:
            raise ValueError("threshold_pt 는 양수여야 합니다.")
        self._threshold = float(threshold_value)
        self._db: Optional[DBControl] = db
        self._owns_db: bool = db is None and manager is None
        self._manager = manager or NotificationManager(db=db, settings=self._settings)

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
        # manager 가 본 클래스 소유이면 함께 close
        try:
            if self._manager is not None and getattr(self._manager, "_owns_db", False):
                self._manager.close()
        except Exception:  # pylint: disable=broad-except
            pass

    def __enter__(self) -> "SentimentAlertWatcher":
        self.db()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @property
    def threshold_pt(self) -> float:
        return self._threshold

    # ------------------------------------------------------------------ core
    def evaluate(self, stock_code: str) -> Optional[NotificationResult]:
        """가장 최근 두 개의 감성 점수를 비교해 임계값 초과 시 알림 전송.

        Returns
        -------
        NotificationResult | None
            발송 시 결과, 발송 대상 아님이면 ``None``.
        """
        if not stock_code:
            raise ValueError("stock_code 는 필수입니다.")

        rows = self.db().fetch_all(
            "SELECT score_date, score FROM sentiment_scores "
            "WHERE stock_code = ? ORDER BY score_date DESC LIMIT 2",
            (stock_code,),
        )
        if len(rows) < 2:
            _LOGGER.debug("감성 점수 시계열이 부족: stock=%s", stock_code)
            return None

        current, previous = rows[0], rows[1]
        try:
            current_score = float(current["score"])
            previous_score = float(previous["score"])
        except (TypeError, ValueError, KeyError) as exc:
            _LOGGER.warning("감성 점수 파싱 실패: %s", exc)
            return None

        delta = current_score - previous_score
        if abs(delta) < self._threshold:
            return None  # 변동 미달 — 발송 대상 아님

        period_label = (
            f"{previous['score_date']} → {current['score_date']}"
        )
        return self._manager.notify_sentiment_shift(
            stock_code=stock_code,
            previous_score=previous_score,
            current_score=current_score,
            period_label=period_label,
        )

    def evaluate_many(self, stock_codes: List[str]) -> List[NotificationResult]:
        """여러 종목을 한 번에 평가. 발송 대상이 아닌 종목은 결과에서 제외."""
        results: List[NotificationResult] = []
        for code in stock_codes or []:
            res = self.evaluate(code)
            if res is not None:
                results.append(res)
        return results
