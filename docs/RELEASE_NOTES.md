# Semi Senti — Release Notes

사용자·운영자가 읽는 **변경 이력**이다. [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따른다.

- **버전:** 기능 단위 완료 시 `web/package.json`의 `version`과 맞추거나, 백엔드만 변경이면 패치(`x.y.z`)만 올린다.
- **작성 시점:** Task·기능 단위 완료 후 **커밋 직전** (`.cursor/rules/dev-workflow-docs-and-git.mdc` 참고).
- **항목:** Task ID(`T-xxx`)·PRD 기능 ID가 있으면 괄호로 표기.

---

## [Unreleased]

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

### Deprecated

### Security

---

## [0.1.0] - 2026-05-17

### Added

- (T-048) Next.js 14 프론트엔드 스캐폴드 (`web/`) — Phase 5 UI 리뉴얼 착수
