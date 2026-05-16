"""``NotificationManager`` (T-041, F-5.1.1, UC-05).

> "매매 시그널(BUY/SELL) 발생 시 텔레그램 API를 통해 즉각 알림을 발송한다."

본 모듈은 ``SignalDecision`` 또는 ``SentimentEngine`` 결과로부터 텔레그램
메시지를 빌드해 ``TelegramClient`` 로 발송하고, 결과(성공/실패/재시도 횟수)
를 ``notifications`` 테이블에 적재한다.

설계
----
- 메시지 빌드 로직(``build_signal_message``)은 *순수 함수* 로 분리하여
  단위 테스트가 용이하게 한다.
- HOLD 시그널은 발송 대상이 아니다 (UC-05 기본 흐름).
- 동일 시그널 중복 발송 방지를 위해 ``signaled_at`` 을 키로 한 dedupe 옵션 제공.
- 발송 실패 시 ``status='FAILED'`` 로 기록하여 UC-05 §E1 "미발송 알림 N건"
  배지 기능(T-039 의 응용)이 추후에 가능하도록 한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from ..config import Settings, get_settings
from ..db import DBControl
from .telegram_client import TelegramClient, TelegramSendError

_LOGGER = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# DTO
# -----------------------------------------------------------------------------


@dataclass
class NotificationRecord:
    """``notifications`` 테이블 row 의 메모리 표현."""

    stock_code: Optional[str]
    channel: str
    event_type: str
    payload: str
    status: str = "PENDING"
    retry_count: int = 0
    last_error: Optional[str] = None
    sent_at: Optional[str] = None

    def to_db_row(self) -> Dict[str, Any]:
        return {
            "stock_code": self.stock_code,
            "channel": self.channel,
            "event_type": self.event_type,
            "payload": self.payload,
            "status": self.status,
            "retry_count": int(self.retry_count),
            "last_error": self.last_error,
            "sent_at": self.sent_at,
        }


@dataclass
class NotificationResult:
    """``NotificationManager.notify_*`` 의 호출 결과."""

    success: bool
    skipped: bool = False
    skip_reason: Optional[str] = None
    record_id: Optional[int] = None
    error: Optional[str] = None
    payload: Optional[str] = None


# -----------------------------------------------------------------------------
# Pure builders (단위 테스트 대상)
# -----------------------------------------------------------------------------


def _format_money(value: Optional[float], currency: str = "KRW") -> str:
    if value is None:
        return "N/A"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "N/A"
    if currency.upper() == "KRW":
        return f"{v:,.0f}원"
    return f"{v:,.2f} {currency}"


def _format_band_diff(price: Optional[float], boundary: Optional[float]) -> str:
    if price is None or boundary in (None, 0):
        return "N/A"
    try:
        diff = (float(price) - float(boundary)) / float(boundary) * 100.0
    except (TypeError, ValueError, ZeroDivisionError):
        return "N/A"
    return f"{diff:+.2f}%"


def build_signal_message(
    *,
    stock_code: str,
    stock_name: str,
    signal_type: str,
    price: Optional[float],
    band_low: Optional[float],
    band_high: Optional[float],
    sentiment_score: Optional[float],
    signaled_at: Optional[str] = None,
    currency: str = "KRW",
) -> str:
    """UC-05 메시지 포맷 그대로의 텔레그램 본문 생성.

    예시 결과::

        🔔 [Semi Senti] 매매 시그널 발생
        ─────────────────────────────
        종목   : SK하이닉스 (000660)
        시그널 : 🟢 BUY
        현재가 : 128,000원
        밴드   : 하단 131,500원 대비 -2.7%
        감성   : -82 (공포 구간)
        시각   : 2026-05-02 14:32
    """
    sig_upper = (signal_type or "").upper()
    if sig_upper == "BUY":
        signal_label = "🟢 BUY"
        boundary_label = "하단"
        boundary = band_low
    elif sig_upper == "SELL":
        signal_label = "🔴 SELL"
        boundary_label = "상단"
        boundary = band_high
    else:
        signal_label = sig_upper or "HOLD"
        boundary_label = "범위"
        boundary = None

    sentiment_text = "N/A"
    if sentiment_score is not None:
        try:
            s = float(sentiment_score)
            zone = (
                "공포 구간" if s <= -34
                else "탐욕 구간" if s >= 34
                else "중립 구간"
            )
            sentiment_text = f"{s:+.0f} ({zone})"
        except (TypeError, ValueError):
            sentiment_text = "N/A"

    when = signaled_at or datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    band_section = (
        f"{boundary_label} {_format_money(boundary, currency)} 대비 "
        f"{_format_band_diff(price, boundary)}"
    ) if boundary is not None else "N/A"

    lines = [
        "🔔 [Semi Senti] 매매 시그널 발생",
        "─" * 25,
        f"종목   : {stock_name} ({stock_code})",
        f"시그널 : {signal_label}",
        f"현재가 : {_format_money(price, currency)}",
        f"밴드   : {band_section}",
        f"감성   : {sentiment_text}",
        f"시각   : {when}",
    ]
    return "\n".join(lines)


def build_sentiment_shift_message(
    *,
    stock_code: str,
    stock_name: str,
    previous_score: float,
    current_score: float,
    delta: float,
    period_label: str = "1시간 내",
) -> str:
    """T-042 감성 점수 급변 경고 본문."""
    direction = "급락" if delta < 0 else "급등"
    arrow = "📉" if delta < 0 else "📈"
    return (
        f"⚠️ {arrow} [Semi Senti] {stock_name}({stock_code}) 감성 지수 {direction}\n"
        f"{previous_score:+.1f} → {current_score:+.1f} (Δ {delta:+.1f}pt, {period_label})"
    )


# -----------------------------------------------------------------------------
# NotificationManager (T-041, T-043)
# -----------------------------------------------------------------------------


class NotificationManager:
    """시그널·감성 이벤트 → 텔레그램 발송 + DB 적재.

    Parameters
    ----------
    db / settings:
        외부 주입 우선. 미지정 시 본 클래스가 직접 생성.
    client:
        ``TelegramClient`` 주입. 테스트에서 mock 객체 주입에 사용.
    """

    EVENT_SIGNAL = "SIGNAL"
    EVENT_SENTIMENT_SHIFT = "SENTIMENT_SHIFT"
    CHANNEL_TELEGRAM = "telegram"

    def __init__(
        self,
        db: Optional[DBControl] = None,
        *,
        client: Optional[TelegramClient] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._db: Optional[DBControl] = db
        self._owns_db: bool = db is None
        self._client = client or TelegramClient(settings=self._settings)

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

    def __enter__(self) -> "NotificationManager":
        self.db()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @property
    def client(self) -> TelegramClient:
        return self._client

    # ------------------------------------------------------------------ signal
    def notify_signal(
        self,
        *,
        stock_code: str,
        signal_type: str,
        price: Optional[float],
        band_low: Optional[float],
        band_high: Optional[float],
        sentiment_score: Optional[float],
        signaled_at: Optional[str] = None,
        stock_name: Optional[str] = None,
        currency: str = "KRW",
        dedupe: bool = True,
    ) -> NotificationResult:
        """BUY/SELL 시그널을 텔레그램으로 발송하고 DB 에 적재.

        - HOLD 는 ``skipped=True`` 로 즉시 반환.
        - 이미 동일 ``signaled_at`` 으로 SENT 된 알림이 있으면 dedupe.
        """
        if not stock_code:
            raise ValueError("stock_code 는 필수입니다.")

        sig_upper = (signal_type or "").upper()
        if sig_upper not in ("BUY", "SELL"):
            return NotificationResult(
                success=False, skipped=True, skip_reason=f"send 대상 아님: {sig_upper}"
            )

        # 종목명 조회 (DB → 없으면 코드로 폴백).
        if stock_name is None:
            row = self.db().fetch_one(
                "SELECT name FROM stocks WHERE stock_code = ?", (stock_code,)
            )
            stock_name = (row or {}).get("name") or stock_code

        # 중복 발송 방지.
        if dedupe and signaled_at:
            already = self.db().fetch_one(
                "SELECT id FROM notifications WHERE stock_code = ? "
                "AND event_type = ? AND status = 'SENT' "
                "AND payload LIKE ? LIMIT 1",
                (stock_code, self.EVENT_SIGNAL, f"%{signaled_at}%"),
            )
            if already is not None:
                return NotificationResult(
                    success=True,
                    skipped=True,
                    skip_reason="이미 발송된 시그널",
                    record_id=int(already["id"]),
                )

        payload = build_signal_message(
            stock_code=stock_code,
            stock_name=str(stock_name),
            signal_type=sig_upper,
            price=price,
            band_low=band_low,
            band_high=band_high,
            sentiment_score=sentiment_score,
            signaled_at=signaled_at,
            currency=currency,
        )
        return self._send_and_record(
            stock_code=stock_code,
            event_type=self.EVENT_SIGNAL,
            payload=payload,
        )

    # ------------------------------------------------------------------ sentiment shift
    def notify_sentiment_shift(
        self,
        *,
        stock_code: str,
        previous_score: float,
        current_score: float,
        period_label: str = "1시간 내",
        stock_name: Optional[str] = None,
    ) -> NotificationResult:
        """감성 점수 ±30pt 이상 급변 경고를 발송한다 (T-042)."""
        if not stock_code:
            raise ValueError("stock_code 는 필수입니다.")

        if stock_name is None:
            row = self.db().fetch_one(
                "SELECT name FROM stocks WHERE stock_code = ?", (stock_code,)
            )
            stock_name = (row or {}).get("name") or stock_code

        delta = float(current_score) - float(previous_score)
        payload = build_sentiment_shift_message(
            stock_code=stock_code,
            stock_name=str(stock_name),
            previous_score=float(previous_score),
            current_score=float(current_score),
            delta=delta,
            period_label=period_label,
        )
        return self._send_and_record(
            stock_code=stock_code,
            event_type=self.EVENT_SENTIMENT_SHIFT,
            payload=payload,
        )

    # ------------------------------------------------------------------ helpers
    def _send_and_record(
        self,
        *,
        stock_code: Optional[str],
        event_type: str,
        payload: str,
    ) -> NotificationResult:
        """공통 발송/적재 헬퍼."""
        record = NotificationRecord(
            stock_code=stock_code,
            channel=self.CHANNEL_TELEGRAM,
            event_type=event_type,
            payload=payload,
            status="PENDING",
            retry_count=0,
        )
        record_id = self.db().insert("notifications", record.to_db_row())

        # 봇이 설정되지 않은 환경 (개발/테스트 또는 토큰 미발급).
        if not self._client.is_configured:
            error_msg = "텔레그램 봇 미설정 (TELEGRAM_BOT_TOKEN/CHAT_ID)"
            self._update_record(record_id, status="FAILED", retry_count=0, error=error_msg)
            _LOGGER.warning("notification skip: %s", error_msg)
            return NotificationResult(
                success=False,
                skipped=True,
                skip_reason=error_msg,
                record_id=record_id,
                payload=payload,
            )

        last_error: Optional[str] = None
        attempt = 0
        for attempt in range(1, self._client.max_retries + 1):
            try:
                self._client.send(payload)
                self._update_record(
                    record_id,
                    status="SENT",
                    retry_count=attempt - 1,  # send 1회 시도 → retry 0
                    error=None,
                )
                _LOGGER.info(
                    "notification SENT: id=%d, type=%s, stock=%s",
                    record_id, event_type, stock_code,
                )
                return NotificationResult(
                    success=True,
                    record_id=record_id,
                    payload=payload,
                )
            except TelegramSendError as exc:
                last_error = str(exc)
                _LOGGER.warning(
                    "notification 시도 실패 %d/%d: id=%d err=%s",
                    attempt, self._client.max_retries, record_id, last_error,
                )

        # 모든 시도 실패
        self._update_record(
            record_id,
            status="FAILED",
            retry_count=self._client.max_retries,
            error=last_error,
        )
        _LOGGER.error(
            "notification FAILED: id=%d, attempts=%d, error=%s",
            record_id, self._client.max_retries, last_error,
        )
        return NotificationResult(
            success=False,
            record_id=record_id,
            error=last_error,
            payload=payload,
        )

    def _update_record(
        self,
        record_id: int,
        *,
        status: str,
        retry_count: int,
        error: Optional[str],
    ) -> None:
        data: Dict[str, Any] = {
            "status": status,
            "retry_count": int(retry_count),
            "last_error": error,
        }
        if status == "SENT":
            data["sent_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        try:
            self.db().update(
                "notifications", data, where="id = ?", where_params=(int(record_id),)
            )
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error("notification 레코드 업데이트 실패: id=%d err=%s", record_id, exc)

    # ------------------------------------------------------------------ inspection
    def list_failed(self, limit: int = 50) -> list:
        """미발송(FAILED) 알림 조회 — 관리자 화면 N건 배지용."""
        return self.db().fetch_all(
            "SELECT id, stock_code, event_type, payload, last_error, retry_count, "
            "created_at FROM notifications WHERE status = 'FAILED' "
            "ORDER BY created_at DESC LIMIT ?",
            (int(limit),),
        )

    def count_failed(self) -> int:
        row = self.db().fetch_one(
            "SELECT COUNT(*) AS cnt FROM notifications WHERE status = 'FAILED'"
        )
        return int((row or {}).get("cnt") or 0)
