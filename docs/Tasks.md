# Semi Senti — Tasks.md

> **마지막 업데이트:** 2026-05-17  
> **전체 진행률:** 48 / 58 완료 (Phase 1-4 완료 · Phase 5 착수)  
> 상태 범례: `⬜ 대기` · `🔄 진행 중` · `✅ 완료` · `🚫 차단됨` · `❌ 제외`

---

## Phase 1 — 데이터 파이프라인 구축 `[ 13 / 13 ]`

> **목표:** 외부 API 수집 → 전처리 → SQLite 캐싱 파이프라인 안정화  
> **예상 기간:** 2주

### 1-1. 프로젝트 초기 세팅

| # | 상태 | 작업 | 우선순위 | 비고 |
|---|------|------|----------|------|
| T-001 | ✅ | Python 가상환경 생성 및 `requirements.txt` 작성 | P1 | Python 3.8+ |
| T-002 | ✅ | 디렉터리 구조 설계 및 초기 폴더 생성 | P1 | `/collector`, `/engine`, `/dashboard`, `/admin`, `/db` |
| T-003 | ✅ | SQLite DB 스키마 설계 및 테이블 생성 스크립트 작성 | P1 | `Financials`, `News`, `Signals`, `Stocks` 테이블 |
| T-004 | ✅ | `DBcontrol` 클래스 구현 (CRUD 공통 인터페이스) | P1 | 모든 모듈의 DB 접근 창구 |

### 1-2. 재무·주가 데이터 수집 (F-1.1)

| # | 상태 | 작업 | 우선순위 | 비고 |
|---|------|------|----------|------|
| T-005 | ✅ | Open DART API 키 발급 및 연동 테스트 | P1 | `.env`로 키 관리 |
| T-006 | ✅ | DART API 재무제표 수집 모듈 구현 | P1 | 매출액·영업이익·PER·PBR·EPS 추출 |
| T-007 | ✅ | yfinance 일별 주가(종가·고가·저가·거래량) 수집 모듈 구현 | P1 | |
| T-008 | ✅ | 결측치 처리 및 단위 통일(원/달러 등) 정규화 로직 구현 | P1 | |
| T-009 | ✅ | 정제된 데이터 SQLite `Financials` 테이블 적재 구현 | P1 | |

### 1-3. 뉴스 데이터 수집 (F-1.2 / F-1.3)

| # | 상태 | 작업 | 우선순위 | 비고 |
|---|------|------|----------|------|
| T-010 | ✅ | 네이버 뉴스 검색 API 키 발급 및 연동 테스트 | P1 | |
| T-011 | ✅ | 종목명 키워드 기반 뉴스 수집 모듈 구현 | P1 | 헤드라인·본문 요약·발행 시간 수집 |
| T-012 | ✅ | BeautifulSoup4로 HTML 태그·특수문자 제거 전처리 구현 | P1 | |
| T-013 | ✅ | SQLite 캐싱 및 TTL 기반 중복 호출 방지 로직 구현 | P1 | API 쿼터 초과 방지 |

---

## Phase 2 — 분석 엔진 개발 `[ 14 / 14 ]`

> **목표:** NLP 감성 스코어링 + 펀더멘털 밴드 + 매매 시그널 로직 구현  
> **예상 기간:** 3주  
> **의존성:** Phase 1 완료 후 착수

### 2-1. NLP 감성 분석 엔진 (F-2.1 / F-2.2)

| # | 상태 | 작업 | 우선순위 | 비고 |
|---|------|------|----------|------|
| T-014 | ✅ | JDK 1.8+ 설치 확인 및 KoNLPy 설치·테스트 | P1 | JVM 메모리 설정 포함 |
| T-015 | ✅ | `SentimentEngine` 클래스 설계 및 뼈대 구현 | P1 | |
| T-016 | ✅ | KoNLPy 형태소 분석으로 명사·형용사 추출 구현 | P1 | |
| T-017 | ✅ | 반도체 특화 감성 사전 초안 작성 | P1 | 감산·수율·HBM·재고·수요·공급 등 가중치 정의 |
| T-018 | ✅ | 키워드 매칭 및 가중치 합산 Raw Score 산출 구현 | P1 | `Raw Score = Σ(키워드 가중치)` |
| T-019 | ✅ | Raw Score → -100 ~ +100 정규화 로직 구현 | P1 | |
| T-020 | ✅ | 일자별·종목별 감성 점수 DB 저장 구현 | P1 | |
| T-021 | ✅ | 반도체 특화 사전 1차 검증 (샘플 뉴스 10건 테스트) | P1 | 점수 방향성 육안 검증 |

### 2-2. 펀더멘털 밴드 및 매매 시그널 로직 (F-3.1 / F-3.2)

| # | 상태 | 작업 | 우선순위 | 비고 |
|---|------|------|----------|------|
| T-022 | ✅ | `SignalLogic` 클래스 설계 및 뼈대 구현 | P1 | |
| T-023 | ✅ | 재무 지표 기반 펀더멘털 밴드(상단·하단) 산출 로직 구현 | P1 | PER·PBR·EPS 활용 |
| T-024 | ✅ | BUY / SELL / HOLD 시그널 분기 로직 구현 | P1 | 소단위명세표 3.1.0 기준 |
| T-025 | ✅ | 시그널 결과 및 타임스탬프 DB `Signals` 테이블 저장 구현 | P1 | |

### 2-3. 다이버전스 탐지 (F-2.3) `[P2]`

| # | 상태 | 작업 | 우선순위 | 비고 |
|---|------|------|----------|------|
| T-026 | ✅ | `DivergenceDetector` 클래스 구현 | P2 | 강세/약세 다이버전스 탐지 |
| T-027 | ✅ | 주가 추세 vs 감성 지수 추세 비교 알고리즘 구현 | P2 | N일 이동 추세 기준 |

---

## Phase 3 — MVP 대시보드 구현 `[ 12 / 12 ]`

> **목표:** Streamlit + TradingView 기반 대시보드 완성 및 통합 테스트  
> **예상 기간:** 2주  
> **의존성:** Phase 2 완료 후 착수

### 3-1. TradingView 차트 컴포넌트 (F-4.1)

| # | 상태 | 작업 | 우선순위 | 비고 |
|---|------|------|----------|------|
| T-028 | ✅ | `SignalChartClass` 설계 및 TradingView API 연동 구현 | P1 | `dashboard/chart.py::SignalChart` |
| T-029 | ✅ | 캔들 차트 렌더링 구현 | P1 | `streamlit-lightweight-charts` Candlestick 시리즈 |
| T-030 | ✅ | BUY(▲ 녹색) / SELL(▼ 적색) 시그널 마커 표시 구현 | P1 | `build_signal_markers` |
| T-031 | ✅ | 마커 호버 시 시그널 근거 팝업 표시 구현 | P1 | 감성 점수·밴드 대비 % 표시 (`_build_signal_tooltip` + Expander) |
| T-032 | ✅ | 다이버전스 마커(황색 ◆ / 보라색 ◆) 오버레이 구현 | P2 | `build_divergence_markers` (T-026 의존 충족) |

### 3-2. 감성 게이지 및 재무 요약 (F-4.2 / F-4.3)

| # | 상태 | 작업 | 우선순위 | 비고 |
|---|------|------|----------|------|
| T-033 | ✅ | `SentimentGauge` 컴포넌트 구현 | P1 | 공포(파랑)/중립(회색)/탐욕(빨강) 색상 코딩 |
| T-034 | ✅ | 감성 게이지 자동 갱신 주기 설정 구현 (5분 interval) | P2 | `streamlit-autorefresh` + sleep 폴백 |
| T-035 | ✅ | 상위 기여 키워드 트렌드 리스트 표시 구현 | P1 | `build_keyword_rows` |
| T-036 | ✅ | 재무 요약 패널 구현 (매출액·영업이익·PER·PBR·EPS) | P1 | `dashboard/financial_panel.py::FinancialSummary` |

### 3-3. 대시보드 통합 및 레이아웃 (F-4.1 ~ F-4.3)

| # | 상태 | 작업 | 우선순위 | 비고 |
|---|------|------|----------|------|
| T-037 | ✅ | `ViewClass` 메인 레이아웃 구성 (1화면 집중 원칙 적용) | P1 | `dashboard/app.py::ViewClass` (wide layout, 차트+게이지+재무 한 화면) |
| T-038 | ✅ | 종목 선택 UI (드롭다운) 및 로딩 스피너 구현 | P1 | `st.selectbox` + `st.spinner` |
| T-039 | ✅ | API 오류·캐시 폴백 시 경고 배너 표시 구현 | P1 | `dashboard/alerts.py::build_stale_message` (info/warning/error 3단계) |

---

## Phase 4 — 확장 기능 `[ 8 / 8 ]`

> **목표:** 알림·사이클 분석·관리자 시스템 추가  
> **예상 기간:** 3주  
> **의존성:** Phase 3 (MVP) 완료 후 착수

### 4-1. 알림 시스템 (F-5.1)

| # | 상태 | 작업 | 우선순위 | 비고 |
|---|------|------|----------|------|
| T-040 | ✅ | 텔레그램 Bot 생성 및 API 토큰 발급 | P2 | `.env.example` 가이드 + `Settings.telegram_*` |
| T-041 | ✅ | `NotificationManager` 클래스 구현 | P2 | `notifier/manager.py` (BUY/SELL UC-05 포맷, dedupe 포함) |
| T-042 | ✅ | 감성 점수 급변(±30pt 이상) 경고 알림 구현 | P2 | `notifier/sentiment_alert.py::SentimentAlertWatcher` |
| T-043 | ✅ | 알림 발송 실패 시 재시도(최대 3회) 및 로그 기록 구현 | P2 | `notifier/telegram_client.py` + `notifications` 테이블 |

### 4-2. 업황 사이클 분석 (F-2.4)

| # | 상태 | 작업 | 우선순위 | 비고 |
|---|------|------|----------|------|
| T-044 | ✅ | `CycleAnalyzer` 클래스 구현 | P2 | `engine/cycle.py` (재고 회전율·YoY 매출·영업이익률 가중합) |
| T-045 | ✅ | 업황 사이클 위치 수치화 및 대시보드 표시 구현 | P2 | `cycle_scores` 테이블 + `dashboard/cycle_panel.py` |

### 4-3. 관리자 시스템 (F-6.1)

| # | 상태 | 작업 | 우선순위 | 비고 |
|---|------|------|----------|------|
| T-046 | ✅ | Admin 종목 관리 UI 구현 (추가·수정·삭제) | P2 | `admin/stock_admin.py` + `dashboard/admin_page.py` 탭1 (yfinance 검증) |
| T-047 | ✅ | 시스템 모니터링 화면 구현 (수집·분석 상태 표시) | P2 | `admin/monitoring.py::SystemMonitor` (수동 갱신 버튼 포함) |

---

## Phase 5 — 프론트엔드 리뉴얼 (Claude 스타일 Next.js 전환) `[ 1 / 11 ]`

> **목표:** 기존 Streamlit 대시보드를 Next.js 14 + Tailwind + Shadcn UI 기반의
> Claude 스타일(Clean / Minimal / Rich Data Visual) SPA로 재구축한다.  
> **백엔드 영향:** Python 분석 엔진(`SentimentEngine`, `SignalLogic`, `DivergenceDetector`,
> `CycleAnalyzer`) 및 SQLite 스키마는 **그대로 유지**. 신규 `web/` 워크스페이스가
> SQLite(`db/semi_senti.sqlite`)를 read-only 로 공유하며, 필요 시 FastAPI 어댑터를 후속 추가한다.  
> **예상 기간:** 3주  
> **의존성:** Phase 1~4 완료 (현재 충족).

### 5-1. 스캐폴드 & 디자인 시스템

| # | 상태 | 작업 | 우선순위 | 비고 |
|---|------|------|----------|------|
| T-048 | ✅ | `web/` 워크스페이스 신설 (Next.js 14 App Router · TS · Tailwind · Shadcn 설정) | P1 | `package.json`, `tsconfig.json`, `next.config.mjs`, `tailwind.config.ts`, `app/globals.css`(Zinc-950 다크 + 시맨틱 시그널 토큰), `components.json`, `lib/types.ts`(`DashboardSnapshot` 미러), `lib/utils.ts`(cn), placeholder `app/page.tsx` |
| T-049 | ⬜ | Shadcn UI 원시 컴포넌트 설치 (button/card/select/tabs/popover/tooltip/dialog/switch/slider/badge/skeleton) | P1 | `components/ui/*` |
| T-050 | ⬜ | `AppShell` / `Sidebar` / `Topbar` / `DashboardShell` 레이아웃 골격 구현 (1화면 집중 grid) | P1 | `viewport-lock`, `glass-card` 유틸 활용 |

### 5-2. 데이터 레이어 (Next.js ↔ SQLite)

| # | 상태 | 작업 | 우선순위 | 비고 |
|---|------|------|----------|------|
| T-051 | ⬜ | `web/lib/db.ts` — `better-sqlite3` read-only 싱글톤 | P1 | 환경변수 `SEMI_SENTI_DB_PATH` |
| T-052 | ⬜ | `web/lib/snapshot.ts` — Python `DashboardSnapshot` 동일 shape 빌더 | P1 | `classify_sentiment` 포팅 포함 |
| T-053 | ⬜ | Route Handler `/api/stocks`, `/api/snapshot/[code]`, `/api/health` 구현 | P1 | no-store, JSON |
| T-054 | ⬜ | `hooks/use-snapshot`, `hooks/use-stocks`, `hooks/use-auto-refresh` (SWR) | P1 | T-034 자동 갱신 매핑 (5분) |

### 5-3. 대시보드 컴포넌트 (Streamlit → React 포팅)

| # | 상태 | 작업 | 우선순위 | 비고 |
|---|------|------|----------|------|
| T-055 | ⬜ | `SentimentGauge`, `KeywordTrend`, `FinancialSummary`, `CyclePanel`, `StaleBanner`, `DivergenceBadge` | P1 | T-033/T-035/T-036/T-045/T-039 매핑 |
| T-056 | ⬜ | `SignalChart` (lightweight-charts) — 캔들 + 펀더멘털 밴드 + BUY/SELL/Divergence 마커 + `SignalMarkerPopover`(근거) | P1 | T-028~T-032 매핑 |

### 5-4. 관리자 & 마이그레이션

| # | 상태 | 작업 | 우선순위 | 비고 |
|---|------|------|----------|------|
| T-057 | ⬜ | `/admin` 페이지 — 종목 CRUD 테이블 + 시스템 모니터 | P2 | T-046/T-047 매핑 |
| T-058 | ⬜ | (조건부) `src/semi_senti/api/` FastAPI 어댑터 — 분석 엔진 트리거가 필요해질 때만 | P2 | Streamlit 대시보드 deprecation 결정 시점 |

---

## 영구 제외 항목

| # | 항목 | 사유 |
|---|------|------|
| ❌ | 증권사 계좌 연동 자동 매매 | 보안 및 법적 책임 문제 (설계서 제약사항 명시) |
| ❌ | 유료 외부 데이터 서비스 연동 | 비용 요구사항 — 무료 쿼터 내 운용 원칙 |

---

## 작업 의존성 흐름

```
[Phase 1 — 파이프라인]
T-001 → T-002 → T-003 → T-004
                    ↓
         T-005~T-009 (재무/주가 수집)
         T-010~T-013 (뉴스 수집 + 캐싱)
                    ↓
[Phase 2 — 분석 엔진]
T-014~T-021 (NLP 감성 엔진)  ─┐
T-022~T-025 (시그널 로직)    ─┤
T-026~T-027 (다이버전스)     ─┘
                    ↓
[Phase 3 — MVP 대시보드]
T-028~T-039 (차트 + 게이지 + 레이아웃)
                    ↓
[Phase 4 — 확장 기능]
T-040~T-043 (알림)
T-044~T-045 (사이클 분석)
T-046~T-047 (관리자 시스템)
                    ↓
[Phase 5 — 프론트엔드 리뉴얼 (Next.js)]
T-048 (스캐폴드) → T-049~T-050 (UI 셸)
                ↓
        T-051~T-054 (데이터 레이어)
                ↓
        T-055~T-056 (대시보드 컴포넌트)
                ↓
        T-057 (관리자) → T-058 (FastAPI, 조건부)
```

---

## 착수 전 환경 요건 체크리스트

> 각 Phase 시작 전 반드시 확인하세요.

- [ ] Python 3.8 이상 설치 확인
- [ ] JDK 1.8 이상 설치 확인 (KoNLPy 구동 필수)
- [ ] 시스템 RAM 8GB 이상 확인
- [ ] Open DART API 키 발급 완료
- [ ] 네이버 개발자 센터 API 키 발급 완료
- [ ] 텔레그램 Bot Token 발급 완료 (Phase 4 착수 전)
- [ ] `.env` 파일로 모든 API 키 관리 (절대 코드에 하드코딩 금지)
