"""SQLite 스키마 정의.

Tasks T-003 요구사항:
    "SQLite DB 스키마 설계 및 테이블 생성 스크립트 작성 | P1 |
    Financials, News, Signals, Stocks 테이블"

설계 원칙
---------
1. **테이블 이름은 snake_case** 로 통일한다(SQLite 권장).
   ─ Tasks 문서의 ``Financials/News/Signals/Stocks`` 는 논리명이며 물리명은 소문자.
2. 모든 외래 키는 ``stocks.stock_code`` 를 참조한다(중앙 DB 데이터 공유 원칙).
3. ``CREATE TABLE IF NOT EXISTS`` 와 ``CREATE INDEX IF NOT EXISTS`` 로
   ``init_database()`` 가 멱등적으로 동작하도록 한다.
4. 캐싱·중복 호출 방지(F-1.3) 를 위해 ``UNIQUE`` 제약을 적극 활용한다.
5. 시그널 도출 로직(F-3.2) 의 ``BUY/SELL/HOLD`` 만 허용하는 ``CHECK`` 를 둔다.
"""

from __future__ import annotations

from typing import Tuple


# 논리 테이블명 ↔ 물리 테이블명 매핑 (외부에 노출).
# - Phase 1-1 핵심 4테이블 + Phase 2-1 의 sentiment_scores (T-020).
# - sentiment_scores 는 "일자별·종목별 감성 점수" 집계 저장용.
ALL_TABLES: Tuple[str, ...] = (
    "stocks",
    "financials",
    "news",
    "signals",
    "sentiment_scores",
    "notifications",
    "cycle_scores",
)


# -----------------------------------------------------------------------------
# DDL 정의 (외부 API 호출 없이 순수 문자열 상수)
# -----------------------------------------------------------------------------

_PRAGMA_STATEMENTS: Tuple[str, ...] = (
    # 외래 키 제약 활성화 (SQLite 는 기본 OFF).
    "PRAGMA foreign_keys = ON;",
)

_CREATE_STOCKS = """
CREATE TABLE IF NOT EXISTS stocks (
    stock_code   TEXT    PRIMARY KEY,                          -- 종목 코드 (예: '005930')
    name         TEXT    NOT NULL,                             -- 종목명 (예: '삼성전자')
    market       TEXT,                                         -- KOSPI / KOSDAQ 등
    is_active    INTEGER NOT NULL DEFAULT 1
                 CHECK (is_active IN (0, 1)),                  -- 분석 대상 활성 여부
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

# Financials: 일별 주가 + 분기 재무지표 스냅샷을 통합 적재.
# - record_date 기준으로 그 시점의 가장 최근 분기 PER/PBR/EPS 등이 함께 들어간다.
# - 일별 주가만 수집된 경우 재무 컬럼은 NULL.
# - PRD F-1.1.3 단위 통일(원/달러) 을 위해 currency 컬럼을 유지.
_CREATE_FINANCIALS = """
CREATE TABLE IF NOT EXISTS financials (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code        TEXT    NOT NULL,
    record_date       TEXT    NOT NULL,                        -- 'YYYY-MM-DD'
    open_price        REAL,
    high_price        REAL,
    low_price         REAL,
    close_price       REAL,
    volume            INTEGER,
    revenue           REAL,                                    -- 매출액
    operating_profit  REAL,                                    -- 영업이익
    per               REAL,
    pbr               REAL,
    eps               REAL,
    currency          TEXT    NOT NULL DEFAULT 'KRW',
    created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (stock_code, record_date),
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE CASCADE
);
"""

# News: 수집된 기사 본문 + Phase 2 에서 채울 감성 점수 컬럼을 미리 NULL 허용으로 보유.
_CREATE_NEWS = """
CREATE TABLE IF NOT EXISTS news (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code           TEXT    NOT NULL,
    title                TEXT    NOT NULL,
    summary              TEXT,
    cleaned_text         TEXT,                                  -- BS4 정제 후 본문
    source               TEXT,                                  -- 'naver_news' 등
    url                  TEXT,
    published_at         TEXT    NOT NULL,                      -- ISO 8601
    collected_at         TEXT    NOT NULL DEFAULT (datetime('now')),
    sentiment_score      REAL,                                  -- -100 ~ +100 (Phase 2)
    sentiment_raw_score  REAL,                                  -- 가중치 합 원본
    UNIQUE (stock_code, url),
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE CASCADE
);
"""

# Signals: 매매 시그널 (F-3.2.2).
# - signal_type 은 PRD §3.2 의 BUY/SELL/HOLD 만 허용.
# - rationale 에는 시그널 근거(예: "현재가 < 밴드하단 & 감성 -82") 를 자유 텍스트로 저장.
_CREATE_SIGNALS = """
CREATE TABLE IF NOT EXISTS signals (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code       TEXT    NOT NULL,
    signal_type      TEXT    NOT NULL
                     CHECK (signal_type IN ('BUY', 'SELL', 'HOLD')),
    price            REAL    NOT NULL,
    band_low         REAL,
    band_high        REAL,
    sentiment_score  REAL,
    rationale        TEXT,
    signaled_at      TEXT    NOT NULL,                          -- ISO 8601
    created_at       TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE CASCADE
);
"""

# SentimentScores (T-020): 일자별·종목별 감성 점수 집계.
# - 감성 분석 엔진이 News 테이블의 row 들을 GROUP BY (stock_code, date) 한 결과를
#   이 테이블에 매일 1건씩 누적한다.
# - top_keywords 는 JSON 문자열로 저장하여 대시보드(F-4.2.3) 에서 디코드해 사용.
_CREATE_SENTIMENT_SCORES = """
CREATE TABLE IF NOT EXISTS sentiment_scores (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code      TEXT    NOT NULL,
    score_date      TEXT    NOT NULL,                          -- 'YYYY-MM-DD'
    score           REAL    NOT NULL,                          -- -100 ~ +100
    raw_score       REAL,                                      -- 정규화 전 합산값
    news_count      INTEGER NOT NULL DEFAULT 0,
    top_keywords    TEXT,                                      -- JSON: [{"word": "...", "weight": ...}, ...]
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (stock_code, score_date),
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE CASCADE
);
"""

# Notifications (T-043, F-5.1):
# - 대상 시그널/감성 변동 이벤트별 발송 결과를 누적 기록한다.
# - status: 'PENDING' | 'SENT' | 'FAILED' (CHECK 제약).
# - retry_count 가 max_retries 에 도달하면 SignalLogic 이 재시도하지 않는다.
_CREATE_NOTIFICATIONS = """
CREATE TABLE IF NOT EXISTS notifications (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code    TEXT,
    channel       TEXT    NOT NULL DEFAULT 'telegram',     -- 'telegram' | 'log' 등
    event_type    TEXT    NOT NULL,                         -- 'SIGNAL' | 'SENTIMENT_SHIFT'
    payload       TEXT,                                     -- 사용자에게 보낸 본문(텍스트)
    status        TEXT    NOT NULL DEFAULT 'PENDING'
                  CHECK (status IN ('PENDING', 'SENT', 'FAILED')),
    retry_count   INTEGER NOT NULL DEFAULT 0,
    last_error    TEXT,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    sent_at       TEXT,
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE SET NULL
);
"""

# CycleScores (T-044, T-045, F-2.4):
# - 분기 단위 업황 사이클 점수(-100 ~ +100) 를 적재한다.
# - phase: 'TROUGH' | 'EARLY_CYCLE' | 'MID_CYCLE' | 'LATE_CYCLE' | 'PEAK' (CHECK).
_CREATE_CYCLE_SCORES = """
CREATE TABLE IF NOT EXISTS cycle_scores (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code          TEXT    NOT NULL,
    score_date          TEXT    NOT NULL,                   -- 'YYYY-MM-DD' (분기 마감일)
    cycle_score         REAL    NOT NULL,                   -- -100 ~ +100
    phase               TEXT    NOT NULL
                        CHECK (phase IN ('TROUGH', 'EARLY_CYCLE',
                                         'MID_CYCLE', 'LATE_CYCLE', 'PEAK')),
    inventory_turnover  REAL,                                -- 재고자산 회전율 (회/연)
    revenue_growth_pct  REAL,                                -- YoY 매출 성장률 (%)
    op_margin_pct       REAL,                                -- 영업이익률 (%)
    note                TEXT,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (stock_code, score_date),
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE CASCADE
);
"""

_INDEX_STATEMENTS: Tuple[str, ...] = (
    "CREATE INDEX IF NOT EXISTS idx_financials_stock_date "
    "ON financials(stock_code, record_date DESC);",
    "CREATE INDEX IF NOT EXISTS idx_news_stock_published "
    "ON news(stock_code, published_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_signals_stock_time "
    "ON signals(stock_code, signaled_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_sentiment_stock_date "
    "ON sentiment_scores(stock_code, score_date DESC);",
    "CREATE INDEX IF NOT EXISTS idx_notifications_stock_time "
    "ON notifications(stock_code, created_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_notifications_status "
    "ON notifications(status, created_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_cycle_stock_date "
    "ON cycle_scores(stock_code, score_date DESC);",
)


# 외부에서 사용할 전체 DDL 묶음 (PRAGMA → CREATE TABLE → CREATE INDEX 순서).
SCHEMA_STATEMENTS: Tuple[str, ...] = (
    *_PRAGMA_STATEMENTS,
    _CREATE_STOCKS,
    _CREATE_FINANCIALS,
    _CREATE_NEWS,
    _CREATE_SIGNALS,
    _CREATE_SENTIMENT_SCORES,
    _CREATE_NOTIFICATIONS,
    _CREATE_CYCLE_SCORES,
    *_INDEX_STATEMENTS,
)
