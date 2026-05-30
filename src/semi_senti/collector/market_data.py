"""한국 주식 OHLCV — pykrx (KRX·네이버 기반) 기본, yfinance 폴백.

PRD v1.2: yfinance → pykrx 전환 (F-1.1.2)
- 채택: pykrx (무료, API 키 불필요, KRX·네이버 기반)
- 미채택: yfinance (Yahoo Finance — 글로벌 서비스 지연·불안정 이슈)
- 봉 주기: 일(1d)·주(1wk)·월(1mo)·년(1y) 만 지원 (분·초봉 무료 소스 미제공)
- 무료 pykrx 기준 약 3,000거래일 (2014년 이후) 제공
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple

from .base import CollectorError

_LOGGER = logging.getLogger(__name__)

ChartIntervalId = Literal["1d", "1wk", "1mo", "1y"]


@dataclass(frozen=True)
class ChartIntervalSpec:
    id: ChartIntervalId
    label_ko: str
    resample_rule: str = ""


CHART_INTERVALS: Tuple[ChartIntervalSpec, ...] = (
    ChartIntervalSpec("1d", "일"),
    ChartIntervalSpec("1wk", "주", "W-FRI"),
    ChartIntervalSpec("1mo", "월", "ME"),
    ChartIntervalSpec("1y", "년", "YE"),
)


def list_chart_intervals() -> List[Dict[str, str]]:
    return [{"id": s.id, "label": s.label_ko, "source": "pykrx"} for s in CHART_INTERVALS]


def get_interval_spec(interval: str) -> ChartIntervalSpec:
    key = (interval or "1d").strip().lower()
    if key in ("1s", "1m", "5m", "15m", "1h"):
        raise CollectorError(
            "분·초봉은 무료 공개 소스에서 제공되지 않습니다. "
            "일·주·월·년봉만 지원합니다."
        )
    for spec in CHART_INTERVALS:
        if spec.id == key:
            return spec
    raise CollectorError(f"지원하지 않는 interval: {interval!r}")


# ---------------------------------------------------------------------------
# pykrx
# ---------------------------------------------------------------------------

def _import_pykrx():
    try:
        from pykrx import stock as pykrx_stock  # type: ignore
        return pykrx_stock
    except ImportError as exc:
        raise CollectorError(
            "'pykrx' 패키지가 필요합니다. pip install pykrx"
        ) from exc


def _pykrx_date_range(*, from_date: Optional[str] = None, days: Optional[int] = None) -> Tuple[str, str]:
    """pykrx 에 전달할 (fromdate, todate) 문자열 쌍 'YYYYMMDD' 형태."""
    today = datetime.now()
    to_date = today.strftime("%Y%m%d")
    if from_date:
        from_str = from_date.replace("-", "")
    elif days:
        from_str = (today - timedelta(days=days)).strftime("%Y%m%d")
    else:
        from_str = "20140101"
    return from_str, to_date


def fetch_pykrx_ohlcv(
    stock_code: str,
    *,
    from_date: Optional[str] = None,
    days: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """pykrx 일봉 OHLCV (고가·저가·시가·종가·거래량).

    Parameters
    ----------
    stock_code: 6자리 KRX 종목코드 (예: '005930')
    from_date: 'YYYYMMDD' 또는 'YYYY-MM-DD' — 시작일 지정 시 사용
    days: 최근 N일 — from_date 미지정 시 사용 (둘 다 없으면 전체 이력)
    """
    pykrx = _import_pykrx()
    from_str, to_str = _pykrx_date_range(from_date=from_date, days=days)

    try:
        df = pykrx.get_market_ohlcv_by_date(from_str, to_str, stock_code)
    except Exception as exc:
        raise CollectorError(f"pykrx 호출 실패 ({stock_code}): {exc}") from exc

    if df is None or df.empty:
        raise CollectorError(f"pykrx 일봉 없음: {stock_code} ({from_str}~{to_str})")

    rows: List[Dict[str, Any]] = []
    for ts, row in df.iterrows():
        try:
            time_val = ts.strftime("%Y-%m-%d")
        except AttributeError:
            time_val = str(ts)[:10]
        try:
            open_p = float(row.get("시가") or row.get("Open") or 0)
            high_p = float(row.get("고가") or row.get("High") or 0)
            low_p = float(row.get("저가") or row.get("Low") or 0)
            close_p = float(row.get("종가") or row.get("Close") or 0)
            volume = int(row.get("거래량") or row.get("Volume") or 0)
        except (KeyError, TypeError, ValueError) as exc:
            _LOGGER.warning("pykrx OHLCV 파싱 스킵 (%s, %s): %s", stock_code, time_val, exc)
            continue
        if close_p <= 0:
            continue
        rows.append(
            {
                "time": time_val,
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "volume": volume,
            }
        )

    if not rows:
        raise CollectorError(f"pykrx 유효 일봉 없음: {stock_code}")

    _LOGGER.debug("pykrx 일봉: %s rows=%d (%s~%s)", stock_code, len(rows), rows[0]["time"], rows[-1]["time"])
    return rows


def fetch_all_daily_history(
    stock_code: str,
    *,
    market: str = "KOSPI",
    from_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """상장 이래 전체 일봉 (pykrx, 기본 2014년 이후)."""
    rows = fetch_pykrx_ohlcv(stock_code, from_date=from_date or "20140101")
    _LOGGER.info(
        "pykrx 전체 일봉: %s rows=%d (%s ~ %s)",
        stock_code,
        len(rows),
        rows[0]["time"],
        rows[-1]["time"],
    )
    return rows


def fetch_recent_daily(
    stock_code: str,
    *,
    market: str = "KOSPI",
    days: int = 30,
) -> List[Dict[str, Any]]:
    """최근 N일 일봉."""
    return fetch_pykrx_ohlcv(stock_code, days=days + 7)  # +7: 주말·공휴일 버퍼


def _resample_daily(rows: Sequence[Dict[str, Any]], rule: str) -> List[Dict[str, Any]]:
    if not rows:
        return []
    try:
        import pandas as pd  # type: ignore
    except ImportError as exc:
        raise CollectorError("pandas 가 필요합니다.") from exc

    df = pd.DataFrame(list(rows))
    df["dt"] = pd.to_datetime(df["time"])
    df = df.set_index("dt").sort_index()
    agg = df.resample(rule).agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
    )
    agg = agg.dropna(subset=["close"])
    out: List[Dict[str, Any]] = []
    for ts, row in agg.iterrows():
        out.append(
            {
                "time": ts.strftime("%Y-%m-%d"),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row["volume"] or 0),
            }
        )
    return out


def fetch_chart_candles(
    stock_code: str,
    *,
    interval: str = "1d",
    market: str = "KOSPI",
    db_rows: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """차트용 OHLCV. ``db_rows`` 가 있으면 PostgreSQL 우선, 없으면 pykrx 직접."""
    if not stock_code:
        raise CollectorError("stock_code 는 필수입니다.")

    spec = get_interval_spec(interval)
    if db_rows:
        daily = list(db_rows)
        note = f"PostgreSQL financials ({len(daily)}일)"
    else:
        daily = fetch_all_daily_history(stock_code, market=market)
        note = f"pykrx 일봉 ({len(daily)}일)"

    if spec.id == "1d":
        rows = daily
    else:
        rows = _resample_daily(daily, spec.resample_rule)
        note = f"{note} → {spec.label_ko} 리샘플"

    first = rows[0]["time"] if rows else None
    last = rows[-1]["time"] if rows else None
    return {
        "stock_code": stock_code,
        "interval": spec.id,
        "time_format": "date",
        "source": "pykrx",
        "note": note,
        "first_date": first,
        "last_date": last,
        "count": len(rows),
        "candles": rows,
    }


def validate_stock_code(
    stock_code: str,
    *,
    market: str = "KOSPI",
) -> Tuple[bool, str]:
    """종목 코드 유효성 (최근 7일 OHLCV 존재 여부)."""
    try:
        rows = fetch_recent_daily(stock_code, market=market, days=7)
    except CollectorError as exc:
        return False, str(exc)
    if not rows:
        return False, "pykrx 응답이 비어 있습니다 (유효하지 않은 코드)."
    return True, ""


# ---------------------------------------------------------------------------
# 하위 호환 — 기존 yfinance 기반 코드 임포트 경로 유지
# ---------------------------------------------------------------------------

def to_yahoo_symbol(stock_code: str, market: str = "KOSPI") -> str:
    """하위 호환 — pykrx 에서는 불필요하나 기존 PriceCollector 에서 참조."""
    code = (stock_code or "").strip()
    upper = (market or "KOSPI").upper()
    suffix = ".KQ" if upper in ("KOSDAQ", "KQ") else ".KS"
    return f"{code}{suffix}"
