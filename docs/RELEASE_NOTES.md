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

### Changed

- `better-sqlite3` → `sql.js` (WASM 기반) 교체: Windows/Node 24 환경에서 네이티브 빌드 문제 해결
- `app/page.tsx` — SQLite API + SWR로 실데이터 연동 (`?code=` 종목 선택)
- `next.config.mjs` — `better-sqlite3` 제거, `sql.js`를 서버 번들에 맞게 정리

### Fixed

### Deprecated

### Security

---

## [0.1.0] - 2026-05-17

### Added

- (T-048) Next.js 14 프론트엔드 스캐폴드 (`web/`) — Phase 5 UI 리뉴얼 착수
