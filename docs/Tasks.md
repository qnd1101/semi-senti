# Semi Senti — Tasks.md (PRD v1.2)

> **마지막 업데이트:** 2026-05-30  
> **전체 진행률:** PRD v1.2 기준 Phase 1~4 완료  
> 상태 범례: `⬜ 대기` · `🔄 진행 중` · `✅ 완료` · `🚫 차단됨` · `❌ 제외`

---

## Phase 1 — 데이터 계층 전환 `[ 완료 ]`

> **목표:** SQLite 제거 → PostgreSQL 기반 수집 안정화, yfinance → pykrx 전환  
> **예상 기간:** 2주

| # | 상태 | 작업 | 우선순위 | 비고 |
|---|------|------|----------|------|
| T-001 | ✅ | Python 가상환경 생성 및 requirements.txt 작성 | P1 | psycopg2-binary, pykrx 추가 |
| T-002 | ✅ | 디렉터리 구조 설계 | P1 | collector, engine, db, api, pipeline, web |
| T-003 | ✅ | PostgreSQL 스키마 설계 및 테이블 생성 (db/schema.py) | P1 | signals에 perspective 컬럼, reasonings 테이블 추가 |
| T-004 | ✅ | DBControl 클래스 재작성 (psycopg2 기반) | P1 | ?→%s 자동 변환, RealDictCursor |
| T-005 | ✅ | Open DART API 연동 | P1 | .env OPEN_DART_API_KEY |
| T-006 | ✅ | DART 재무제표 수집 모듈 | P1 | 매출액·영업이익·PER·PBR·EPS |
| T-007 | ✅ | pykrx 일별 주가 수집 모듈 (F-1.1.2) | P1 | KRX·네이버 기반, API 키 불필요 |
| T-008 | ✅ | 결측치·단위 통일 정규화 | P1 | DataNormalizer |
| T-009 | ✅ | PostgreSQL financials UPSERT | P1 | (stock_code, record_date) 충돌 키 |
| T-010 | ✅ | 네이버 뉴스 API 연동 | P1 | |
| T-011 | ✅ | 뉴스 수집 모듈 | P1 | 헤드라인·본문요약·발행시간 |
| T-012 | ✅ | BeautifulSoup4 HTML 정제 | P1 | |
| T-013 | ✅ | PostgreSQL 캐싱 및 TTL 중복 호출 방지 | P1 | F-1.3 |

---

## Phase 2 — 분석 엔진 고도화 `[ 완료 ]`

> **목표:** 다중 관점 시그널 (SHORT/MID/LONG) + PRD §F-3.2 가중치 모델

| # | 상태 | 작업 | 우선순위 | 비고 |
|---|------|------|----------|------|
| T-014 | ✅ | KoNLPy 설치·테스트 | P1 | JDK 1.8+ 필요 |
| T-015 | ✅ | SentimentEngine 구현 | P1 | |
| T-016 | ✅ | 형태소 분석 (명사·형용사 추출) | P1 | |
| T-017 | ✅ | 반도체 특화 감성 사전 | P1 | 감산·수율·HBM·재고 등 |
| T-018 | ✅ | 키워드 매칭 Raw Score 산출 | P1 | |
| T-019 | ✅ | -100~+100 정규화 | P1 | tanh 기반 |
| T-020 | ✅ | 감성 점수 DB 저장 | P1 | sentiment_scores UPSERT |
| T-021 | ✅ | 감성 사전 1차 검증 | P1 | |
| T-022 | ✅ | SignalLogic 클래스 재설계 (SHORT/MID/LONG) | P1 | PRD §F-3.2 가중치 모델 |
| T-023 | ✅ | FundamentalBand 산출 (PER×EPS) | P1 | |
| T-024 | ✅ | 관점별 BUY/SELL/HOLD 판정 (±25pt 임계) | P1 | PRD §F-3.2 의사코드 |
| T-025 | ✅ | 시그널 DB 저장 (perspective 컬럼 포함) | P1 | |
| T-026 | ✅ | DivergenceDetector 구현 | P2 | |
| T-027 | ✅ | 주가·감성 추세 비교 알고리즘 | P2 | |

---

## Phase 3 — Reasoning 통합 `[ 완료 ]`

> **목표:** Gemini API 연동, 프롬프트 설계, 폴백 안정화 (F-3.3)

| # | 상태 | 작업 | 우선순위 | 비고 |
|---|------|------|----------|------|
| T-028 | ✅ | reasonings 테이블 설계 (prompt_hash, is_fallback) | P1 | F-3.3.3 |
| T-029 | ✅ | ReasoningEngine 구현 (engine/reasoning.py) | P1 | |
| T-030 | ✅ | Gemini API 구조화 프롬프트 생성 (JSON+한국어 지시문) | P1 | |
| T-031 | ✅ | 응답 검증 후 reasonings 저장 | P1 | |
| T-032 | ✅ | API 키 누락·실패 시 규칙 기반 폴백 (F-3.3.2) | P1 | GEMINI_API_KEY 미설정 시 비활성 |

---

## Phase 4 — MVP UI 완성 `[ 완료 ]`

> **목표:** Claude 스타일 다크 대시보드 + 1화면 완성 (F-4.1~F-4.3)

| # | 상태 | 작업 | 우선순위 | 비고 |
|---|------|------|----------|------|
| T-033 | ✅ | GET /api/snapshot/{code} 엔드포인트 (FastAPI) | P1 | 종목 전체 스냅샷 |
| T-034 | ✅ | Next.js 14 + Tailwind + Shadcn UI 스캐폴드 (web/) | P1 | |
| T-035 | ✅ | 다크 테마 글로벌 CSS (Zinc-950, glass-card, signal semantics) | P1 | |
| T-036 | ✅ | SentimentGauge 컴포넌트 (SVG 반원, 공포/중립/탐욕) | P1 | |
| T-037 | ✅ | KeywordTrend 컴포넌트 (방향성 칩) | P1 | |
| T-038 | ✅ | SignalCard 컴포넌트 x3 (SHORT/MID/LONG + 근거 Popover) | P1 | |
| T-039 | ✅ | FinancialSummary 컴포넌트 (재무 요약 + 밴드 위치) | P1 | |
| T-040 | ✅ | SignalChart 컴포넌트 (lightweight-charts 캔들 + 마커 + 밴드) | P1 | |
| T-041 | ✅ | CyclePanel 컴포넌트 (업황 사이클 진행 바) | P1 | |
| T-042 | ✅ | 1화면 메인 페이지 (app/page.tsx, 자동 갱신 60초) | P1 | |

---

## Phase 5 — 확장 기능 `[ 대기 ]`

> **목표:** 알림·괴리 고도화·사이클 심화·관리자 시스템

| # | 상태 | 작업 | 우선순위 | 비고 |
|---|------|------|----------|------|
| T-043 | ⬜ | 텔레그램 알림 (F-5.1) | P2 | BUY/SELL 시 발송 |
| T-044 | ⬜ | 다이버전스 고도화 (F-2.3) | P2 | 마커 UI 연동 |
| T-045 | ⬜ | 업황 사이클 심화 분석 (F-2.4) | P2 | |
| T-046 | ✅ | 관리자 페이지 /admin (종목 CRUD + 시스템 모니터) | P2 | Next.js /admin + FastAPI 엔드포인트 |

---

## 영구 제외 항목

| # | 항목 | 사유 |
|---|------|------|
| ❌ | 증권사 계좌 연동 자동 매매 | 보안 및 법적 책임 |
| ❌ | 유료 외부 데이터 서비스 | 비용 요구사항 |
