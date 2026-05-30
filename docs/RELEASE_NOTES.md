# Semi Senti — Release Notes

사용자·운영자가 읽는 **변경 이력**이다. [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따른다.

- **버전:** 백엔드 변경 시 `pyproject.toml` 패치(`x.y.z`)를 올린다.
- **작성 시점:** Task·기능 단위 완료 후 **커밋 직전** (`.cursor/rules/dev-workflow-docs-and-git.mdc` 참고).
- **항목:** Task ID(`T-xxx`)·PRD 기능 ID가 있으면 괄호로 표기.

---

## [Unreleased]

### Added (T-046 관리자 페이지)

- **Next.js `/admin` 관리자 페이지** — 종목 관리 탭 + 시스템 상태 탭 (T-046)
  - 종목 테이블: 추가·활성/비활성 토글·수동 갱신·삭제
  - 시스템 상태: 테이블 행 수, 종목별 데이터 신선도 (주가·뉴스·시그널·감성)
- **FastAPI 관리자 엔드포인트 보강**
  - `GET /api/stocks?include_inactive=true` — 비활성 종목 포함 조회
  - `GET /api/stocks/{code}` — 개별 종목 조회
  - `PATCH /api/stocks/{code}` — 종목 메타 수정 (name/market/is_active)
- 백엔드 SQL 플레이스홀더 수정 (`?` → `%s`, `is_active = 1` → `is_active = TRUE`)

### Added (PRD v1.2 구현)

- **PostgreSQL 전환** — SQLite 완전 제거, psycopg2 기반 `DBControl` 재작성 (F-1.3, §4.2)
- **pykrx 주가 수집** — yfinance → pykrx (KRX·네이버 기반, API 키 불필요, 약 3,000거래일) (F-1.1.2)
- **다중 관점 시그널 (SHORT/MID/LONG)** — PRD §F-3.2 가중치 모델 구현 (±25pt 임계, signals.perspective 컬럼) (T-022~T-024)
- **Gemini API Reasoning** — `engine/reasoning.py` 신규, `reasonings` 테이블, 폴백 템플릿 지원 (F-3.3)
- **GET /api/snapshot/{code}** — 종목 전체 스냅샷 (가격·재무·감성·3관점시그널·근거·사이클) (F-4.1~F-4.3)
- **Next.js 14 대시보드 재구축** — `web/` 신규, Shadcn UI + TradingView Lightweight Charts + 1화면 레이아웃 (F-4.1~F-4.3)
- Claude 스타일 다크 테마 (Zinc-950, glass-card, 시맨틱 시그널 컬러 BUY/SELL/HOLD)
- 자동 갱신 60초 (NEXT_PUBLIC_AUTO_REFRESH_SECONDS)

### Changed

- `db/schema.py` — PostgreSQL DDL, signals 테이블 perspective 컬럼 추가, reasonings 테이블 신규
- `settings.py` — `database_url` (PostgreSQL DSN), `gemini_api_key`, `pykrx_date_from`, 다중 관점 임계값 추가
- `.env.example` — PostgreSQL·Gemini·pykrx 설정 추가
- `run_windows.bat` — Next.js 대시보드 동시 실행 지원
- `requirements.txt` — psycopg2-binary, pykrx, google-generativeai 추가

---

### Added (구 이력)

- 기본 종목(삼성전자·SK하이닉스) 자동 등록 — `/api/stocks` 조회 시 DB가 비어 있으면 Python API로 등록
- 종목 선택 시 **on-demand 수집** — DB에 주가·재무가 없으면 `/api/snapshot`이 Python `/api/sync/{code}` 호출 후 표시
- 주가 수집 **yfinance → pykrx** (KRX·네이버, API 키 불필요)
- 기동 시 **전체 일봉** `financials` 적재 (`collect_full_history_and_store`, 약 3,000일)
- 차트: 일·주·월·년 (분봉 제거 — pykrx 미제공)
- `run_windows.bat` / `run_linux.sh` — Next.js와 함께 Python API(포트 8000) 자동 기동

### Changed

- 주가 수집 **pykrx → yfinance** 복귀 (Yahoo Finance `005930.KS` 형식, API 키 불필요)
- `db_seed.py` — 더미 financials 제거, 스키마·기본 종목 등록만 수행 (실데이터는 API 파이프라인)
- `manual_refresh` — DART 재무 수집 단계 추가
- `.env` — `PRICE_POLL_INTERVAL_SECONDS`, `LIVE_DATA_ENABLED` 설정 추가
- `web/.env.local.example` — 대시보드 자동 갱신 기본 60초
- DART 재무 수집기 개선 — 주식총수 조회(`stockTotqy` API), 재무 데이터 기반 PER/PBR 자동 계산 (지수 API 빈 응답 대응)
- DB 파일명 통일 — `db/semi_senti.sqlite` → `db/semisenti.db` (README, 웹 설정 예시 반영)
- `scripts/seed_demo_data.py` 간소화 — bootstrap 모듈 래퍼로 재작성 (중복 제거)

### Removed

- **모든 UI** — `web/`(Next.js), `src/semi_senti/dashboard/`(Streamlit), `dashboard` CLI 서브커맨드, Streamlit 의존성
- `db_seed.py` 더미 financials 시딩 (가짜 주가·재무 데이터)

### Deprecated

### Security

---

## [0.2.0] - 2026-05-17

### Added

- Cursor 규칙: Git 필수 커밋·푸시(`version-control-mandatory.mdc`) 및 릴리즈 노트 작성 워크플로(`dev-workflow` §4)
- `docs/RELEASE_NOTES.md` 변경 이력 템플릿
- (T-049) Shadcn UI 원시 컴포넌트 11종 설치 — button/card/select/tabs/popover/tooltip/dialog/switch/slider/badge/skeleton
- (T-050) 대시보드 레이아웃 셸 구현 — `AppShell`/`Sidebar`/`Topbar`/`DashboardShell`/`StockSelector`
- (T-051~T-054) Next 데이터 레이어 — `sql.js` read-only 싱글톤, `snapshot` 빌더, `/api/stocks`·`/api/snapshot/[code]`·`/api/health`, SWR 훅 및 메인 페이지 실데이터 연동
- (T-055) 대시보드 카드 6종 — `SentimentGauge`(SVG 반원), `KeywordTrend`, `FinancialSummary`, `CyclePanel`, `StaleBanner`, `DivergenceBadge`
- (T-056) `SignalChart` (lightweight-charts v4.2 캔들+밴드+마커) + `SignalMarkerPopover` (클릭 시 시그널 근거 표시)
- (T-057) `/admin` 관리자 페이지 — 종목 CRUD 테이블(`StockTable`), 시스템 모니터(`SystemMonitor`), 탭 UI + API routes (`/api/admin/stocks`, `/api/admin/system`)
- (T-058) Python FastAPI 어댑터 (`src/semi_senti/api/`) — health, 종목 CRUD, 시스템 상태, 수동 갱신(가격·뉴스·감성·시그널·사이클) + Next.js `/py-api/*` 프록시 rewrite
- `run_windows.bat` — Windows 1-click 실행 스크립트 (환경 체크, 가상환경 자동 생성, 의존성 설치, .env 샘플 복사, 포트 충돌 확인, 서버 시작 + 브라우저 오픈)
- `run_linux.sh` — Linux/macOS 1-click 실행 스크립트 (환경 체크, 가상환경/의존성 자동 설치, 백그라운드 실행 옵션, chmod +x 가이드 포함)

### Changed

- `README.md` 한국어 전면 재작성 — Quick Start(사용자 대상 1-click 실행 가이드), Development Setup(개발자 대상 수동 설치), Configuration(환경 변수 표), Troubleshooting(자주 발생하는 오류 6종), 디렉토리 구조, 기능 개요, 사용 시나리오, Scripts Reference 섹션 구조화
- `README.md` 전면 개편 — Phase 5 완료 기준 아키텍처·Next.js/FastAPI/CLI·DB 경로 통일·기본 종목(DART corp_code) 안내
- Python 3.12 버전 고정 — `run_windows.bat` 및 `run_linux.sh` 가상환경 생성 시 Python 3.12 명시적 사용, README.md 요구사항 업데이트
- `better-sqlite3` → `sql.js` (WASM 기반) 교체: Windows/Node 24 환경에서 네이티브 빌드 문제 해결
- `app/page.tsx` — SQLite API + SWR로 실데이터 연동 (`?code=` 종목 선택)
- `next.config.mjs` — `better-sqlite3` 제거, `sql.js`를 서버 번들에 맞게 정리

### Fixed

- DART 재무 적재 시 `financials` UPSERT 가 주가(OHLCV) 컬럼을 `NULL`로 덮어쓰던 문제 수정 — 재무 필드만 갱신

### Removed

- `setup.bat`, `setup.sh` 제거 — `run_windows.bat`, `run_linux.sh`로 대체됨에 따라 구형 스크립트 삭제

---

## [0.1.0] - 2026-05-17

### Added

- (T-048) Next.js 14 프론트엔드 스캐폴드 (`web/`) — Phase 5 UI 리뉴얼 착수
