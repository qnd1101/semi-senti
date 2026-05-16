# -*- coding: utf-8 -*-
"""Register default semiconductor stocks (UTF-8 safe on Windows)."""
from __future__ import annotations

from semi_senti.db import DBControl

STOCKS = (
    ("005930", "삼성전자", "KOSPI"),
    ("000660", "SK하이닉스", "KOSPI"),
)


def main() -> None:
    db = DBControl()
    for code, name, market in STOCKS:
        db.upsert(
            "stocks",
            {
                "stock_code": code,
                "name": name,
                "market": market,
                "is_active": 1,
            },
            conflict_columns=["stock_code"],
        )
    for row in db.fetch_all(
        "SELECT stock_code, name, market FROM stocks WHERE is_active = 1 ORDER BY stock_code"
    ):
        print(row)


if __name__ == "__main__":
    main()
