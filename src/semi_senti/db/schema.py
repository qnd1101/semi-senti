"""PostgreSQL 스키마 정의.

PRD v1.2 변경사항
-----------------
- SQLite → PostgreSQL (F-1.3, §4.2)
- signals 테이블: perspective(단기/중기/장기) 컬럼 추가 (F-3.2)
- reasonings 테이블 신규 추가 (F-3.3)
- 인덱스 기준: PRD F-1.3.4

설계 원칙
---------
1. 테이블 이름은 snake_case.
2. 모든 외래 키는 stocks.stock_code 를 참조한다.
3. CREATE TABLE IF NOT EXISTS 와 CREATE INDEX IF NOT EXISTS 로 멱등 동작.
4. UPSERT 충돌 방지용 UNIQUE 제약 적극 활용.
5. BUY/SELL/HOLD 만 허용하는 CHECK 제약.
"""

from __future__ import annotations

from typing import Tuple


ALL_TABLES: Tuple[str, ...] = (
    "stocks",
    "financials",
    "news",
    "signals",
    "sentiment_scores",
    "notifications",
    "cycle_scores",
    "reasonings",
)


# -----------------------------------------------------------------------------
# DDL 정의
# -----------------------------------------------------------------------------

_CREATE_STOCKS = """
CREATE TABLE IF NOT EXISTS stocks (
    stock_code   TEXT        PRIMARY KEY,
    name         TEXT        NOT NULL,
    market       TEXT,
    is_active    INTEGER     NOT NULL DEFAULT 1
                 CHECK (is_active IN (0, 1)),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

# Financials: 일별 주가 + 분기 재무지표 스냅샷 통합.
# - record_date 기준 그 시점 최근 분기 PER/PBR/EPS 포함.
# - 일별 주가만 수집된 경우 재무 컬럼은 NULL.
# - PRD F-1.1.3 단위 통일용 currency 컬럼.
_CREATE_FINANCIALS = """
CREATE TABLE IF NOT EXISTS financials (
    id                BIGSERIAL   PRIMARY KEY,
    stock_code        TEXT        NOT NULL,
    record_date       DATE        NOT NULL,
    open_price        DOUBLE PRECISION,
    high_price        DOUBLE PRECISION,
    low_price         DOUBLE PRECISION,
    close_price       DOUBLE PRECISION,
    volume            BIGINT,
    revenue           DOUBLE PRECISION,
    operating_profit  DOUBLE PRECISION,
    per               DOUBLE PRECISION,
    pbr               DOUBLE PRECISION,
    eps               DOUBLE PRECISION,
    currency          TEXT        NOT NULL DEFAULT 'KRW',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (stock_code, record_date),
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE CASCADE
);
"""

# News: 기사 본문 + Phase 2 감성 점수 컬럼.
_CREATE_NEWS = """
CREATE TABLE IF NOT EXISTS news (
    id                   BIGSERIAL   PRIMARY KEY,
    stock_code           TEXT        NOT NULL,
    title                TEXT        NOT NULL,
    summary              TEXT,
    cleaned_text         TEXT,
    source               TEXT,
    url                  TEXT,
    published_at         TIMESTAMPTZ NOT NULL,
    collected_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sentiment_score      DOUBLE PRECISION,
    sentiment_raw_score  DOUBLE PRECISION,
    UNIQUE (stock_code, url),
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE CASCADE
);
"""

# Signals: 매매 시그널 (F-3.2).
# - perspective: 'SHORT' | 'MID' | 'LONG' (PRD §F-3.2 다중 관점)
# - signal_type: 'BUY' | 'SELL' | 'HOLD'
# - score: 관점별 가중치 계산 결과 점수 (PRD §6 Perspective Score)
_CREATE_SIGNALS = """
CREATE TABLE IF NOT EXISTS signals (
    id               BIGSERIAL   PRIMARY KEY,
    stock_code       TEXT        NOT NULL,
    perspective      TEXT        NOT NULL DEFAULT 'SHORT'
                     CHECK (perspective IN ('SHORT', 'MID', 'LONG')),
    signal_type      TEXT        NOT NULL
                     CHECK (signal_type IN ('BUY', 'SELL', 'HOLD')),
    score            DOUBLE PRECISION,
    price            DOUBLE PRECISION NOT NULL,
    band_low         DOUBLE PRECISION,
    band_high        DOUBLE PRECISION,
    sentiment_score  DOUBLE PRECISION,
    rationale        TEXT,
    signaled_at      TIMESTAMPTZ NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE CASCADE
);
"""

# SentimentScores (T-020): 일자별·종목별 감성 점수 집계.
_CREATE_SENTIMENT_SCORES = """
CREATE TABLE IF NOT EXISTS sentiment_scores (
    id              BIGSERIAL   PRIMARY KEY,
    stock_code      TEXT        NOT NULL,
    score_date      DATE        NOT NULL,
    score           DOUBLE PRECISION NOT NULL,
    raw_score       DOUBLE PRECISION,
    news_count      INTEGER     NOT NULL DEFAULT 0,
    top_keywords    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (stock_code, score_date),
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE CASCADE
);
"""

# Notifications (T-043, F-5.1).
_CREATE_NOTIFICATIONS = """
CREATE TABLE IF NOT EXISTS notifications (
    id            BIGSERIAL   PRIMARY KEY,
    stock_code    TEXT,
    channel       TEXT        NOT NULL DEFAULT 'telegram',
    event_type    TEXT        NOT NULL,
    payload       TEXT,
    status        TEXT        NOT NULL DEFAULT 'PENDING'
                  CHECK (status IN ('PENDING', 'SENT', 'FAILED')),
    retry_count   INTEGER     NOT NULL DEFAULT 0,
    last_error    TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at       TIMESTAMPTZ,
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE SET NULL
);
"""

# CycleScores (T-044, T-045, F-2.4).
_CREATE_CYCLE_SCORES = """
CREATE TABLE IF NOT EXISTS cycle_scores (
    id                  BIGSERIAL   PRIMARY KEY,
    stock_code          TEXT        NOT NULL,
    score_date          DATE        NOT NULL,
    cycle_score         DOUBLE PRECISION NOT NULL,
    phase               TEXT        NOT NULL
                        CHECK (phase IN ('TROUGH', 'EARLY_CYCLE',
                                         'MID_CYCLE', 'LATE_CYCLE', 'PEAK')),
    inventory_turnover  DOUBLE PRECISION,
    revenue_growth_pct  DOUBLE PRECISION,
    op_margin_pct       DOUBLE PRECISION,
    note                TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (stock_code, score_date),
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE CASCADE
);
"""

# Reasonings (F-3.3): Gemini API 생성 투자 판단 근거.
# - prompt_hash: 프롬프트 해시(회귀 검증용)
# - is_fallback: True 면 규칙 기반 폴백 텍스트
_CREATE_REASONINGS = """
CREATE TABLE IF NOT EXISTS reasonings (
    id            BIGSERIAL   PRIMARY KEY,
    stock_code    TEXT        NOT NULL,
    perspective   TEXT        NOT NULL
                  CHECK (perspective IN ('SHORT', 'MID', 'LONG')),
    signal_type   TEXT        NOT NULL
                  CHECK (signal_type IN ('BUY', 'SELL', 'HOLD')),
    reasoning     TEXT        NOT NULL,
    prompt_hash   TEXT,
    model_version TEXT,
    is_fallback   BOOLEAN     NOT NULL DEFAULT FALSE,
    generated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code) ON DELETE CASCADE
);
"""

_INDEX_STATEMENTS: Tuple[str, ...] = (
    # PRD F-1.3.4 기본 인덱스
    "CREATE INDEX IF NOT EXISTS idx_financials_stock_date "
    "ON financials(stock_code, record_date DESC);",
    "CREATE INDEX IF NOT EXISTS idx_news_stock_published "
    "ON news(stock_code, published_at DESC);",
    # PRD F-1.3.4: signals(stock_code, perspective, signal_at desc)
    "CREATE INDEX IF NOT EXISTS idx_signals_stock_perspective_time "
    "ON signals(stock_code, perspective, signaled_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_sentiment_stock_date "
    "ON sentiment_scores(stock_code, score_date DESC);",
    "CREATE INDEX IF NOT EXISTS idx_notifications_stock_time "
    "ON notifications(stock_code, created_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_notifications_status "
    "ON notifications(status, created_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_cycle_stock_date "
    "ON cycle_scores(stock_code, score_date DESC);",
    "CREATE INDEX IF NOT EXISTS idx_reasonings_stock_perspective "
    "ON reasonings(stock_code, perspective, generated_at DESC);",
)


SCHEMA_STATEMENTS: Tuple[str, ...] = (
    _CREATE_STOCKS,
    _CREATE_FINANCIALS,
    _CREATE_NEWS,
    _CREATE_SIGNALS,
    _CREATE_SENTIMENT_SCORES,
    _CREATE_NOTIFICATIONS,
    _CREATE_CYCLE_SCORES,
    _CREATE_REASONINGS,
    *_INDEX_STATEMENTS,
)
