"""FastAPI 어댑터 — 메인 앱 + 라우터 (T-058).

Next.js 프론트엔드에서 Python 분석 엔진(감성분석·시그널·사이클·다이버전스)
기능을 HTTP API로 호출할 수 있게 한다.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..admin import StockAdmin, StockAdminError, SystemMonitor
from ..config import get_settings

_LOGGER = logging.getLogger(__name__)

# ────────────────────────── Request / Response models ──────────────────────────


class StockCreateRequest(BaseModel):
    stock_code: str = Field(..., pattern=r"^\d{6}$")
    name: str = Field(..., min_length=1)
    market: str = Field(default="KOSPI")
    validate_with_yfinance: bool = Field(default=False)


class StockToggleRequest(BaseModel):
    stock_code: str = Field(..., pattern=r"^\d{6}$")
    is_active: bool


class RefreshRequest(BaseModel):
    stock_code: str = Field(..., pattern=r"^\d{6}$")
    market: str = Field(default="KOSPI")
    news_query: Optional[str] = None
    run_signal: bool = True
    run_sentiment: bool = True
    run_cycle: bool = True


# ────────────────────────── Lifespan ──────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    _LOGGER.info("Semi Senti FastAPI 시작")
    yield
    _LOGGER.info("Semi Senti FastAPI 종료")


# ────────────────────────── App ──────────────────────────

app = FastAPI(
    title="Semi Senti API",
    description="반도체 감성분석 시스템 — Python 엔진 어댑터",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ────────────────────────── Health ──────────────────────────


@app.get("/health")
async def health():
    settings = get_settings()
    return {"status": "ok", "db": str(settings.sqlite_path)}


# ────────────────────────── Stock CRUD ──────────────────────────


@app.get("/api/stocks")
async def list_stocks():
    """활성+비활성 종목 목록."""
    try:
        with StockAdmin() as admin:
            stocks = admin.list_stocks(include_inactive=True)
        return stocks
    except StockAdminError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/stocks", status_code=201)
async def add_stock(req: StockCreateRequest):
    """종목 추가 (yfinance 검증 선택)."""
    try:
        with StockAdmin() as admin:
            row = admin.add_stock(
                stock_code=req.stock_code,
                name=req.name,
                market=req.market,
                validate_with_yfinance=req.validate_with_yfinance,
            )
        return row
    except StockAdminError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/api/stocks/toggle")
async def toggle_stock(req: StockToggleRequest):
    """종목 활성/비활성 토글."""
    try:
        with StockAdmin() as admin:
            admin.update_stock(stock_code=req.stock_code, is_active=req.is_active)
        return {"stock_code": req.stock_code, "is_active": req.is_active}
    except StockAdminError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/stocks/{stock_code}")
async def delete_stock(stock_code: str):
    """종목 삭제 (CASCADE)."""
    try:
        with StockAdmin() as admin:
            admin.delete_stock(stock_code)
        return {"deleted": stock_code}
    except StockAdminError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ────────────────────────── System Monitor ──────────────────────────


@app.get("/api/system/status")
async def system_status():
    """시스템 상태 보고서."""
    try:
        with SystemMonitor() as mon:
            report = mon.status_report()
        return {
            "generated_at": report.generated_at,
            "db_path": report.db_path,
            "table_counts": report.table_counts,
            "failed_notifications": report.failed_notifications,
            "stocks": [
                {
                    "stock_code": s.stock_code,
                    "name": s.name,
                    "market": s.market,
                    "is_active": s.is_active,
                    "last_price_at": s.last_price_at,
                    "last_news_at": s.last_news_at,
                    "last_signal_at": s.last_signal_at,
                    "last_sentiment_date": s.last_sentiment_date,
                    "signal_count": s.signal_count,
                    "news_count": s.news_count,
                }
                for s in report.stocks
            ],
            "warnings": report.warnings,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ────────────────────────── Manual Refresh ──────────────────────────


@app.post("/api/refresh")
async def manual_refresh(req: RefreshRequest) -> Dict[str, Any]:
    """수동 갱신 (UC-07): 가격·뉴스·감성·시그널·사이클 전체 파이프라인 실행."""
    try:
        with SystemMonitor() as mon:
            result = mon.manual_refresh(
                stock_code=req.stock_code,
                market=req.market,
                news_query=req.news_query,
                run_signal=req.run_signal,
                run_sentiment=req.run_sentiment,
                run_cycle=req.run_cycle,
            )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
