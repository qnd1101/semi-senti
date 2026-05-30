"""기본 분석 종목 정의 (PRD §2: 삼성전자·SK하이닉스)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple


@dataclass(frozen=True)
class DefaultStock:
    """기본 종목 메타데이터."""

    stock_code: str
    name: str
    market: str = "KOSPI"
    corp_code: str = ""
    news_query: str = ""

    def __post_init__(self) -> None:
        if not self.news_query:
            object.__setattr__(self, "news_query", f"{self.name} HBM 반도체")


DEFAULT_STOCKS: Tuple[DefaultStock, ...] = (
    DefaultStock(
        stock_code="005930",
        name="삼성전자",
        market="KOSPI",
        corp_code="00126380",
        news_query="삼성전자 HBM 반도체",
    ),
    DefaultStock(
        stock_code="000660",
        name="SK하이닉스",
        market="KOSPI",
        corp_code="00164779",
        news_query="SK하이닉스 HBM 반도체",
    ),
)


def get_default_stock(stock_code: str) -> Optional[DefaultStock]:
    """종목코드로 기본 종목 메타를 조회한다."""
    code = (stock_code or "").strip()
    for item in DEFAULT_STOCKS:
        if item.stock_code == code:
            return item
    return None


def iter_default_stocks(codes: Optional[Sequence[str]] = None) -> Tuple[DefaultStock, ...]:
    """지정 코드만 필터링해 기본 종목 목록을 반환한다."""
    if not codes:
        return DEFAULT_STOCKS
    wanted = {c.strip() for c in codes if c and c.strip()}
    return tuple(s for s in DEFAULT_STOCKS if s.stock_code in wanted)


def ensure_default_stocks_registered(db) -> None:
    """기본 종목(삼성전자·SK하이닉스)을 stocks 테이블에 upsert."""
    for stock in DEFAULT_STOCKS:
        db.upsert(
            "stocks",
            {
                "stock_code": stock.stock_code,
                "name": stock.name,
                "market": stock.market,
                "is_active": 1,
            },
            conflict_columns=["stock_code"],
            update_columns=["name", "market", "is_active"],
        )
