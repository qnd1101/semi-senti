"""데이터 수집 계층 (DART, 네이버 뉴스, yfinance).

Phase 1-2 / 1-3 산출물:

- :class:`DartFinancialCollector` (T-005, T-006)
- :class:`PriceCollector`         (T-007)
- :class:`NaverNewsCollector`     (T-010, T-011, T-013)
- :class:`TextCleaner`            (T-012)
- :class:`DataNormalizer`         (T-008)

사용 예::

    from semi_senti.collector import PriceCollector, NaverNewsCollector

    with PriceCollector() as pc:
        pc.collect_and_store("005930", market="KOSPI", stock_name="삼성전자")

    with NaverNewsCollector() as nc:
        nc.collect_and_store("005930", query="삼성전자 HBM", stock_name="삼성전자")
"""

from .base import BaseCollector, CollectorError
from .cleaner import TextCleaner
from .dart import DartFinancialCollector
from .news import NaverNewsCollector
from .normalizer import DataNormalizer
from .price import PriceCollector

__all__ = [
    "BaseCollector",
    "CollectorError",
    "TextCleaner",
    "DataNormalizer",
    "DartFinancialCollector",
    "PriceCollector",
    "NaverNewsCollector",
]
