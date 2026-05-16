"""대시보드 데이터 어댑터 (UI ↔ DB 분리 계층).

본 모듈은 Streamlit 컴포넌트가 SQLite 스키마(``financials``, ``signals``,
``sentiment_scores``, ``stocks``) 를 직접 알 필요가 없도록 데이터 조회/가공을
한 곳으로 모은 *Pure-Python* 어댑터다.

설계 원칙
---------
- UI 의존성 0 (streamlit/plotly import 금지) → 단위 테스트 용이
- 모든 DB 쿼리는 ``DBControl`` 을 통해서만 수행 (PRD §4.2 중앙 DB 원칙)
- API 단절·캐시 폴백 상태(``StaleStatus``) 를 같이 반환하여 대시보드가
  경고 배너(T-039) 를 그릴 수 있도록 한다 (UC-01 §E1, F-1.3.3)
- 분석 엔진(``SignalLogic`` / ``DivergenceDetector``) 호출 실패 시에도
  대시보드가 멈추지 않도록 try/except 로 감싸 빈 결과를 반환한다.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..config import Settings, get_settings
from ..db import DBControl, DBControlError
from ..engine import (
    Band,
    DivergenceDetector,
    DivergenceResult,
    FundamentalBand,
    SentimentEngine,
    SignalLogic,
)

_LOGGER = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# DTO 정의 (UI 컴포넌트가 그대로 받아쓰는 dict-friendly 컨테이너)
# -----------------------------------------------------------------------------


@dataclass
class StaleStatus:
    """캐시/폴백 상태. 대시보드 상단 경고 배너(T-039) 의 입력값.

    Attributes
    ----------
    is_stale:
        가장 최근 데이터의 신선도가 임계 시간을 초과했는가.
    last_updated:
        마지막 데이터 시각(ISO 문자열). 없으면 ``None``.
    hours_old:
        ``last_updated`` 기준 경과 시간(시간 단위). 없으면 ``None``.
    message:
        사용자 노출용 경고 메시지(없으면 빈 문자열).
    """

    is_stale: bool = False
    last_updated: Optional[str] = None
    hours_old: Optional[float] = None
    message: str = ""


@dataclass
class DashboardSnapshot:
    """대시보드 한 화면을 그리는 데 필요한 모든 데이터의 묶음.

    UI 컴포넌트는 본 객체만 받아 자기 책임 영역만 그린다.
    """

    stock_code: str
    stock_name: str
    candles: List[Dict[str, Any]] = field(default_factory=list)
    signals: List[Dict[str, Any]] = field(default_factory=list)
    divergences: List[Dict[str, Any]] = field(default_factory=list)
    sentiment: Dict[str, Any] = field(default_factory=dict)
    financial: Dict[str, Any] = field(default_factory=dict)
    band: Dict[str, Any] = field(default_factory=dict)
    stale: StaleStatus = field(default_factory=StaleStatus)
    generated_at: str = ""


# -----------------------------------------------------------------------------
# 감성 점수 → 공포/중립/탐욕 분류 (T-033 공통 로직, UI 미사용 환경에서도 호출)
# -----------------------------------------------------------------------------

# UC-03 §감성 게이지: -100~-34 공포 / -33~+33 중립 / +34~+100 탐욕
_SENTIMENT_THRESHOLDS = (
    (-34.0, "FEAR", "공포"),
    (33.0, "NEUTRAL", "중립"),
    (100.0, "GREED", "탐욕"),
)


def classify_sentiment(score: Optional[float]) -> Dict[str, Any]:
    """감성 점수를 (label_en, label_ko, color) 분류 정보로 변환.

    - 점수가 ``None`` 인 경우 'UNKNOWN' 반환 (대시보드는 회색 처리).
    """
    if score is None:
        return {"key": "UNKNOWN", "label_ko": "데이터 없음", "color": "#9CA3AF"}
    try:
        s = float(score)
    except (TypeError, ValueError):
        return {"key": "UNKNOWN", "label_ko": "데이터 없음", "color": "#9CA3AF"}

    s = max(-100.0, min(100.0, s))
    for upper, key, label_ko in _SENTIMENT_THRESHOLDS:
        if s <= upper:
            color = {
                "FEAR": "#2563EB",     # 파랑
                "NEUTRAL": "#6B7280",  # 회색
                "GREED": "#DC2626",    # 빨강
            }[key]
            return {"key": key, "label_ko": label_ko, "color": color}
    # 안전망 (이 분기는 닿지 않아야 정상)
    return {"key": "NEUTRAL", "label_ko": "중립", "color": "#6B7280"}


# -----------------------------------------------------------------------------
# DataProvider
# -----------------------------------------------------------------------------


class DataProvider:
    """대시보드 데이터 공급자 (DB → 컴포넌트 어댑터).

    Parameters
    ----------
    db:
        외부에서 주입할 ``DBControl``. 미지정 시 본 클래스가 직접 열고 닫는다.
    settings:
        주입할 ``Settings``. 미지정 시 ``get_settings()``.
    stale_after_hours:
        이 시간을 초과한 데이터는 ``StaleStatus.is_stale=True`` 로 표시.
    """

    def __init__(
        self,
        db: Optional[DBControl] = None,
        *,
        settings: Optional[Settings] = None,
        stale_after_hours: float = 24.0,
    ) -> None:
        self._settings = settings or get_settings()
        self._db: Optional[DBControl] = db
        self._owns_db: bool = db is None
        self._stale_after_hours = max(0.5, float(stale_after_hours))

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

    def __enter__(self) -> "DataProvider":
        self.db()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ------------------------------------------------------------------ stocks (T-038)
    def list_active_stocks(self) -> List[Dict[str, Any]]:
        """``stocks`` 테이블에서 활성 종목 목록 조회 (드롭다운 데이터).

        - 비활성/오류 시 빈 리스트를 반환하여 UI 가 fallback dropdown 을
          사용할 수 있게 한다.
        """
        try:
            rows = self.db().fetch_all(
                "SELECT stock_code, name, market FROM stocks "
                "WHERE is_active = 1 ORDER BY name ASC"
            )
            return rows
        except DBControlError as exc:
            _LOGGER.warning("stocks 조회 실패: %s", exc)
            return []

    # ------------------------------------------------------------------ candles (T-029)
    def fetch_candles(self, stock_code: str, *, limit: int = 180) -> List[Dict[str, Any]]:
        """TradingView Lightweight Charts 가 요구하는 캔들 시계열 반환.

        반환 포맷::

            [{"time": "YYYY-MM-DD", "open": ..., "high": ..., "low": ..., "close": ..., "volume": ...}]
        """
        if not stock_code:
            return []
        try:
            rows = self.db().fetch_all(
                "SELECT record_date, open_price, high_price, low_price, close_price, volume "
                "FROM financials WHERE stock_code = ? "
                "AND close_price IS NOT NULL "
                "ORDER BY record_date DESC LIMIT ?",
                (stock_code, int(limit)),
            )
        except DBControlError as exc:
            _LOGGER.warning("financials 조회 실패: stock=%s err=%s", stock_code, exc)
            return []

        # 차트 라이브러리는 시간 오름차순을 기대한다.
        rows = list(reversed(rows))
        candles: List[Dict[str, Any]] = []
        for r in rows:
            time_str = str(r.get("record_date") or "")[:10]
            close = r.get("close_price")
            if not time_str or close is None:
                continue
            candles.append(
                {
                    "time": time_str,
                    # OHLC 결측값은 close 로 폴백 (yfinance 부분 결측 케이스 대응)
                    "open": float(r.get("open_price") or close),
                    "high": float(r.get("high_price") or close),
                    "low": float(r.get("low_price") or close),
                    "close": float(close),
                    "volume": int(r.get("volume") or 0),
                }
            )
        return candles

    # ------------------------------------------------------------------ signals (T-030, T-031)
    def fetch_signals(self, stock_code: str, *, limit: int = 60) -> List[Dict[str, Any]]:
        """차트 위에 그릴 BUY/SELL/HOLD 마커 데이터.

        반환 포맷::

            [{
                "time": "YYYY-MM-DD",            # 마커 위치
                "signal_type": "BUY"|"SELL",    # HOLD 는 마커 미표시 → 제외
                "price": ..., "band_low": ..., "band_high": ...,
                "sentiment_score": ...,
                "rationale": "...",
                "tooltip": "감성 -82, 밴드 하단 대비 -2.7%",
            }]
        """
        if not stock_code:
            return []
        try:
            rows = self.db().fetch_all(
                "SELECT signal_type, price, band_low, band_high, sentiment_score, "
                "rationale, signaled_at FROM signals WHERE stock_code = ? "
                "ORDER BY signaled_at DESC LIMIT ?",
                (stock_code, int(limit)),
            )
        except DBControlError as exc:
            _LOGGER.warning("signals 조회 실패: stock=%s err=%s", stock_code, exc)
            return []

        rows = list(reversed(rows))
        markers: List[Dict[str, Any]] = []
        for r in rows:
            sig = str(r.get("signal_type") or "").upper()
            if sig not in ("BUY", "SELL"):
                continue  # UC-02: HOLD 는 마커 미표시
            time_str = self._extract_date(r.get("signaled_at"))
            if not time_str:
                continue
            markers.append(
                {
                    "time": time_str,
                    "signal_type": sig,
                    "price": _safe_float(r.get("price")),
                    "band_low": _safe_float(r.get("band_low")),
                    "band_high": _safe_float(r.get("band_high")),
                    "sentiment_score": _safe_float(r.get("sentiment_score")),
                    "rationale": str(r.get("rationale") or ""),
                    "tooltip": _build_signal_tooltip(r),
                }
            )
        return markers

    # ------------------------------------------------------------------ divergence (T-032)
    def fetch_divergences(self, stock_code: str) -> List[Dict[str, Any]]:
        """다이버전스 마커 데이터 (강세=황색◆ / 약세=보라색◆).

        - 현재 ``DivergenceDetector`` 는 1건의 최신 결과만 반환하므로
          1건짜리 리스트 또는 빈 리스트를 반환한다.
        - 탐지기 예외 시 빈 리스트를 반환하여 UI 를 멈추지 않는다.
        """
        if not stock_code:
            return []
        try:
            with DivergenceDetector(db=self.db(), settings=self._settings) as dd:
                result: DivergenceResult = dd.detect(stock_code)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.warning("divergence 탐지 실패: stock=%s err=%s", stock_code, exc)
            return []

        if not result.detected:
            return []

        # 최신 가격이 표시된 일자에 마커를 위치시킨다.
        last_date_row = self._fetch_one(
            "SELECT record_date FROM financials WHERE stock_code = ? "
            "AND close_price IS NOT NULL ORDER BY record_date DESC LIMIT 1",
            (stock_code,),
        )
        time_str = self._extract_date(
            last_date_row.get("record_date") if last_date_row else None
        ) or datetime.utcnow().strftime("%Y-%m-%d")

        color = "#FBBF24" if result.divergence_type == "BULLISH_OPPORTUNITY" else "#8B5CF6"
        label = "기회" if result.divergence_type == "BULLISH_OPPORTUNITY" else "주의"
        return [
            {
                "time": time_str,
                "divergence_type": result.divergence_type,
                "price_change_pct": result.price_change_pct,
                "sentiment_change_pt": result.sentiment_change_pt,
                "window_days": result.window_days,
                "color": color,
                "label": label,
                "tooltip": (
                    f"{label} 다이버전스 ({result.window_days}일): "
                    f"주가 {result.price_change_pct:+.2f}% / 감성 {result.sentiment_change_pt:+.2f}pt"
                ),
                "note": result.note,
            }
        ]

    # ------------------------------------------------------------------ sentiment (T-033, T-035)
    def fetch_sentiment(self, stock_code: str) -> Dict[str, Any]:
        """게이지 + 키워드 트렌드 데이터.

        반환 포맷::

            {
                "score": -78.0,
                "raw_score": -19.2,
                "score_date": "2026-05-15",
                "news_count": 12,
                "classification": {"key": "FEAR", "label_ko": "공포", "color": "#2563EB"},
                "top_keywords": [{"word": "감산", "weight": 2.0, "count": 4, "contribution": 8.0}, ...],
            }
        """
        empty = {
            "score": None,
            "raw_score": None,
            "score_date": None,
            "news_count": 0,
            "classification": classify_sentiment(None),
            "top_keywords": [],
        }
        if not stock_code:
            return empty

        try:
            with SentimentEngine(db=self.db(), settings=self._settings) as se:
                row = se.get_latest_score(stock_code)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.warning("sentiment 조회 실패: stock=%s err=%s", stock_code, exc)
            return empty

        if not row:
            return empty

        score = _safe_float(row.get("score"))
        keywords = _parse_top_keywords(row.get("top_keywords"))
        return {
            "score": score,
            "raw_score": _safe_float(row.get("raw_score")),
            "score_date": str(row.get("score_date") or ""),
            "news_count": int(row.get("news_count") or 0),
            "classification": classify_sentiment(score),
            "top_keywords": keywords[: int(self._settings.sentiment_top_keyword_limit)],
        }

    # ------------------------------------------------------------------ financial summary (T-036)
    def fetch_financial_summary(self, stock_code: str) -> Dict[str, Any]:
        """재무 요약 패널 데이터 (매출액·영업이익·PER·PBR·EPS + 현재가).

        - 가장 최근 ``financials`` 행에서 비-NULL 값들을 컬럼별로 collect 한다.
        - ``revenue/operating_profit`` 등 분기 지표는 거래일마다 채워지지
          않을 수 있어 컬럼별 가장 최근 비-NULL 값을 별도로 조회한다.
        """
        empty = {
            "current_price": None,
            "record_date": None,
            "revenue": None,
            "operating_profit": None,
            "per": None,
            "pbr": None,
            "eps": None,
            "currency": "KRW",
        }
        if not stock_code:
            return empty

        try:
            latest_row = self._fetch_one(
                "SELECT record_date, close_price, currency "
                "FROM financials WHERE stock_code = ? AND close_price IS NOT NULL "
                "ORDER BY record_date DESC LIMIT 1",
                (stock_code,),
            )
        except DBControlError as exc:
            _LOGGER.warning("financial summary 조회 실패: stock=%s err=%s", stock_code, exc)
            return empty
        if not latest_row:
            return empty

        result = dict(empty)
        result["current_price"] = _safe_float(latest_row.get("close_price"))
        result["record_date"] = self._extract_date(latest_row.get("record_date"))
        result["currency"] = str(latest_row.get("currency") or "KRW")

        # 컬럼별 최신 비-NULL 값 별도 조회.
        for col in ("revenue", "operating_profit", "per", "pbr", "eps"):
            try:
                row = self._fetch_one(
                    f"SELECT {col} FROM financials WHERE stock_code = ? "
                    f"AND {col} IS NOT NULL ORDER BY record_date DESC LIMIT 1",
                    (stock_code,),
                )
            except DBControlError:
                row = None
            if row is not None:
                result[col] = _safe_float(row.get(col))
        return result

    # ------------------------------------------------------------------ band (F-3.1, F-4.3.2)
    def fetch_band(self, stock_code: str) -> Dict[str, Any]:
        """차트 오버레이용 펀더멘털 밴드 (상단·하단·중앙).

        - 분석 엔진을 즉시 호출하여 최신 밴드를 산출한다.
        - 산출 실패 시 ``method='unavailable'`` 인 빈 dict 반환.
        """
        empty = {
            "band_low": None,
            "band_high": None,
            "band_mid": None,
            "method": "unavailable",
            "sample_size": 0,
        }
        if not stock_code:
            return empty
        try:
            with FundamentalBand(db=self.db(), settings=self._settings) as fb:
                band: Band = fb.compute(stock_code)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.warning("band 산출 실패: stock=%s err=%s", stock_code, exc)
            return empty
        return {
            "band_low": band.band_low,
            "band_high": band.band_high,
            "band_mid": band.band_mid,
            "method": band.method,
            "sample_size": band.sample_size,
        }

    # ------------------------------------------------------------------ stale status (T-039)
    def compute_stale_status(self, stock_code: str) -> StaleStatus:
        """가장 최신 가격 갱신 시각 기준으로 폴백 경고를 산출.

        UC-01 §E1 — "데이터가 [최종 갱신 시각] 기준입니다" 메시지.
        """
        if not stock_code:
            return StaleStatus()
        row = self._fetch_one(
            "SELECT MAX(updated_at) AS last_at FROM financials WHERE stock_code = ?",
            (stock_code,),
        )
        last_at_raw = row.get("last_at") if row else None
        if not last_at_raw:
            return StaleStatus(
                is_stale=True,
                last_updated=None,
                hours_old=None,
                message="아직 수집된 데이터가 없습니다.",
            )

        last_dt = _parse_iso(last_at_raw)
        if last_dt is None:
            return StaleStatus(is_stale=True, last_updated=str(last_at_raw))

        delta = datetime.utcnow() - last_dt
        hours_old = max(0.0, delta.total_seconds() / 3600.0)
        is_stale = delta > timedelta(hours=self._stale_after_hours)
        message = ""
        if is_stale:
            message = (
                f"외부 API 갱신이 지연되었습니다. 약 {hours_old:.1f}시간 전 데이터 기준으로 표시됩니다."
            )
        return StaleStatus(
            is_stale=is_stale,
            last_updated=last_dt.strftime("%Y-%m-%d %H:%M:%S"),
            hours_old=round(hours_old, 2),
            message=message,
        )

    # ------------------------------------------------------------------ aggregator
    def get_snapshot(
        self,
        stock_code: str,
        *,
        candle_limit: int = 180,
        signal_limit: int = 60,
    ) -> DashboardSnapshot:
        """한 번의 호출로 대시보드가 필요로 하는 모든 데이터를 조립한다."""
        if not stock_code:
            raise ValueError("stock_code 는 필수입니다.")

        stock_row = self._fetch_one(
            "SELECT stock_code, name FROM stocks WHERE stock_code = ?",
            (stock_code,),
        )
        stock_name = (stock_row or {}).get("name") or stock_code

        snapshot = DashboardSnapshot(
            stock_code=stock_code,
            stock_name=str(stock_name),
            candles=self.fetch_candles(stock_code, limit=candle_limit),
            signals=self.fetch_signals(stock_code, limit=signal_limit),
            divergences=self.fetch_divergences(stock_code),
            sentiment=self.fetch_sentiment(stock_code),
            financial=self.fetch_financial_summary(stock_code),
            band=self.fetch_band(stock_code),
            stale=self.compute_stale_status(stock_code),
            generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        )
        return snapshot

    # ------------------------------------------------------------------ analyze on demand
    def refresh_signal(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """필요 시 ``SignalLogic.detect_and_store`` 를 즉시 실행.

        - 관리자 화면(UC-07) 또는 캐시 미스 보강 용도로 활용.
        - 실패 시 ``None`` 반환(예외 전파 X) — 대시보드는 계속 동작해야 한다.
        """
        try:
            with SignalLogic(db=self.db(), settings=self._settings) as sl:
                decision = sl.detect_and_store(stock_code)
            return {
                "signal_type": decision.signal_type,
                "rationale": decision.rationale,
                "signaled_at": decision.signaled_at,
            }
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.warning("refresh_signal 실패: stock=%s err=%s", stock_code, exc)
            return None

    # ------------------------------------------------------------------ helpers
    def _fetch_one(self, sql: str, params) -> Optional[Dict[str, Any]]:
        try:
            return self.db().fetch_one(sql, params)
        except DBControlError as exc:
            _LOGGER.warning("DB 조회 실패: %s", exc)
            return None

    @staticmethod
    def _extract_date(value: Any) -> Optional[str]:
        """ISO 형식 문자열에서 YYYY-MM-DD 부분만 추출."""
        if value is None:
            return None
        text = str(value)
        if len(text) < 10:
            return None
        return text[:10]


# -----------------------------------------------------------------------------
# 모듈 레벨 헬퍼
# -----------------------------------------------------------------------------


def _safe_float(value: Any) -> Optional[float]:
    """``None``/문자열/숫자 모두를 안전하게 float 로 변환."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_iso(value: Any) -> Optional[datetime]:
    """SQLite의 ``datetime('now')`` 또는 ISO 문자열을 datetime 으로 파싱."""
    if value is None:
        return None
    text = str(value).replace("T", " ").split(".")[0]
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            return datetime.strptime(text[:10], "%Y-%m-%d")
        except ValueError:
            return None


def _parse_top_keywords(raw: Any) -> List[Dict[str, Any]]:
    """``sentiment_scores.top_keywords`` JSON 컬럼을 리스트로 디코드."""
    if not raw:
        return []
    if isinstance(raw, list):
        return [dict(item) for item in raw if isinstance(item, dict)]
    try:
        decoded = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []
    if not isinstance(decoded, list):
        return []
    return [dict(item) for item in decoded if isinstance(item, dict)]


def _build_signal_tooltip(row: Dict[str, Any]) -> str:
    """T-031: 마커 호버 시 표시할 근거 문자열.

    예) "감성 -82 / 현재가 128,000 / 밴드 하단 131,500 대비 -2.7%"
    """
    parts: List[str] = []
    sent = _safe_float(row.get("sentiment_score"))
    if sent is not None:
        parts.append(f"감성 {sent:+.1f}")
    price = _safe_float(row.get("price"))
    if price is not None:
        parts.append(f"현재가 {price:,.0f}")

    band_low = _safe_float(row.get("band_low"))
    band_high = _safe_float(row.get("band_high"))
    sig = str(row.get("signal_type") or "").upper()
    if sig == "BUY" and band_low and price is not None and band_low != 0:
        diff_pct = (price - band_low) / band_low * 100.0
        parts.append(f"밴드 하단 {band_low:,.0f} 대비 {diff_pct:+.2f}%")
    elif sig == "SELL" and band_high and price is not None and band_high != 0:
        diff_pct = (price - band_high) / band_high * 100.0
        parts.append(f"밴드 상단 {band_high:,.0f} 대비 {diff_pct:+.2f}%")

    return " / ".join(parts) if parts else "근거 정보 없음"
