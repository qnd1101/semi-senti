# Phase 5 — Frontend Renewal · 핸드오프 문서

> **작성:** 2026-05-17 03:09 (KST)
> **목적:** 새 채팅에서 작업을 끊김 없이 이어가기 위한 인계 문서.
> **이 파일은 임시 인계용입니다.** Phase 5 종료 시 또는 후속 정리 시 삭제 가능.

---

## 0. TL;DR (다음 채팅에 들어갈 때 이거만 읽어도 됨)

- 프로젝트: **Semi Senti** — 반도체 특화 NLP 감성 + 펀더멘털 매매 시그널 서비스.
- Phase 1~4 (Python 백엔드 · Streamlit 대시보드) **100% 완료**.
- Phase 5 = 프론트엔드 리뉴얼: Streamlit → **Next.js 14 + Tailwind + Shadcn UI + Lucide React** (Claude 스타일 다크).
- 현 위치: **T-051 ~ T-054 ✅ 완료** (데이터 레이어 + API + SWR).
- 다음 작업: **T-055 (소형 대시보드 카드들) → T-056 (`SignalChart` + 마커 Popover)**.

---

## 1. 프로젝트 컨텍스트 (백엔드 — 변경 금지)

### 분석 엔진 (Python `src/semi_senti/`)
| 모듈 | 역할 |
|---|---|
| `SentimentEngine` | KoNLPy 기반 뉴스 형태소 분석 + 반도체 특화 사전 → 일자별/종목별 감성 점수 (-100 ~ +100) |
| `SignalLogic` | `현재가 < 밴드하단 AND 감성 < -70` → BUY · `현재가 > 밴드상단 AND 감성 > +70` → SELL · 그 외 HOLD |
| `DivergenceDetector` | 주가 추세 vs 감성 지수 추세 괴리 탐지 (강세 = amber, 약세 = violet) |
| `CycleAnalyzer` | 재고 회전율 + YoY 매출 → 반도체 업황 사이클 위치 수치화 |

### SQLite 스키마 (`db/semi_senti.sqlite`)
| 테이블 | 핵심 컬럼 |
|---|---|
| `Stocks` | stock_code, name, market, is_active |
| `Financials` | revenue, operating_income, per, pbr, eps, band_low, band_high |
| `News` | headline, summary, published_at, sentiment_score, top_keywords |
| `Signals` | kind(BUY/SELL/HOLD), price, reason, ts |
| `cycle_scores` | score, label, inventory_turnover, yoy_revenue |

### UI 친화 DTO (이미 백엔드에 있음 — 그대로 미러링)
`src/semi_senti/dashboard/data_provider.py::DashboardSnapshot` 의 필드:
`candles · signals · divergences · sentiment · financial · band · stale · generated_at`
→ 이 그대로 `web/lib/types.ts` 에 TypeScript 1:1 미러링 완료.

---

## 2. UX/UI 핵심 요구사항 (PRD §4.3 발췌 · 강제)

1. **1화면 집중 (Viewport Lock)**: 차트 + 게이지 + 재무가 스크롤 없이 `100vh` 안에 다 들어가야 함.
2. **Claude 스타일 다크**: Zinc-950 베이스 + Glassmorphism 카드 (`backdrop-blur`).
3. **시맨틱 색상 토큰** (`web/tailwind.config.ts` + `web/app/globals.css`):
   - BUY / Greed → `signal-buy` (emerald)
   - SELL / Fear → `signal-sell` (rose)
   - HOLD / Neutral → `signal-hold` (zinc)
   - Divergence Bullish → `divergence-bullish` (amber)
   - Divergence Bearish → `divergence-bearish` (violet)
4. **마커 근거 노출**: BUY(▲) · SELL(▼) · Divergence(◆) 클릭/호버 시 Shadcn `Popover` 로 산출 근거(현재가·밴드·감성 점수·기여 키워드).
5. **i18n 대비**: 한글 하드코딩 지양, 메시지 키/상수로 추출 가능한 형태 유지.

---

## 3. 디렉터리 구조 (확정)

```text
semi-senti/
├─ src/semi_senti/          # (기존) Python 백엔드 — 변경 금지
├─ db/semi_senti.sqlite     # (기존) SQLite — Next.js 가 read-only 공유
├─ docs/                    # PRD / UseCases / Tasks (SSOT)
│  └─ handoff/2026-05-17-phase5-frontend-renewal.md  ← 이 파일
└─ web/                     # ⭐ Phase 5 프론트엔드
   ├─ app/
   │  ├─ layout.tsx                 ✅ 다크 강제 + Korean locale
   │  ├─ globals.css                ✅ Zinc-950 + 시맨틱 토큰 + glass-card / viewport-lock
   │  ├─ page.tsx                   ✅ placeholder (컬러 스와치 6개)
   │  ├─ admin/page.tsx             ⬜ T-057
   │  └─ api/
   │     ├─ stocks/route.ts         ⬜ T-053
   │     ├─ snapshot/[code]/route.ts ⬜ T-053
   │     └─ health/route.ts         ⬜ T-053
   ├─ components/
   │  ├─ ui/                        ⬜ T-049 (Shadcn CLI 설치)
   │  ├─ layout/
   │  │  ├─ app-shell.tsx           ⬜ T-050
   │  │  ├─ sidebar.tsx             ⬜ T-050
   │  │  └─ topbar.tsx              ⬜ T-050
   │  ├─ dashboard/
   │  │  ├─ dashboard-shell.tsx     ⬜ T-050
   │  │  ├─ signal-chart.tsx        ⬜ T-056
   │  │  ├─ signal-marker-popover.tsx ⬜ T-056
   │  │  ├─ sentiment-gauge.tsx     ⬜ T-055
   │  │  ├─ keyword-trend.tsx       ⬜ T-055
   │  │  ├─ financial-summary.tsx   ⬜ T-055
   │  │  ├─ cycle-panel.tsx         ⬜ T-055
   │  │  ├─ divergence-badge.tsx    ⬜ T-055
   │  │  ├─ stale-banner.tsx        ⬜ T-055
   │  │  └─ stock-selector.tsx      ⬜ T-050
   │  └─ admin/
   │     ├─ stock-table.tsx         ⬜ T-057
   │     └─ system-monitor.tsx      ⬜ T-057
   ├─ hooks/
   │  ├─ use-snapshot.ts            ⬜ T-054
   │  ├─ use-stocks.ts              ⬜ T-054
   │  └─ use-auto-refresh.ts        ⬜ T-054 (5분 polling, T-034 매핑)
   ├─ lib/
   │  ├─ db.ts                      ⬜ T-051 (sql.js read-only, WASM 기반)
   │  ├─ snapshot.ts                ⬜ T-052 (DashboardSnapshot 빌더 포팅)
   │  ├─ classify-sentiment.ts      ⬜ T-052 (data_provider.classify_sentiment 포팅)
   │  ├─ types.ts                   ✅ DashboardSnapshot 1:1 미러
   │  ├─ format.ts                  ⬜ 통화/숫자/날짜 포매터
   │  └─ utils.ts                   ✅ cn() 헬퍼
   ├─ public/                       ⬜ (필요 시)
   ├─ tailwind.config.ts            ✅
   ├─ postcss.config.mjs            ✅
   ├─ next.config.mjs               ✅
   ├─ tsconfig.json                 ✅
   ├─ components.json               ✅ Shadcn CLI 설정 (zinc baseColor)
   ├─ package.json                  ✅
   ├─ .env.local.example            ✅
   ├─ .gitignore                    ✅
   └─ README.md                     ✅
```

---

## 4. 컴포넌트 트리 & 데이터 흐름 (확정)

### 컴포넌트 트리

```text
<RootLayout>                              app/layout.tsx (html.dark + 폰트)
└─ <AppShell>
   ├─ <Sidebar>                           종목 선택 · 페이지 라우팅 · 갱신 설정
   │  ├─ <StockSelector/>                 (Shadcn Select)
   │  ├─ <AutoRefreshSwitch/>             (Switch + Slider)
   │  └─ <NavTabs/>                       (Tabs: 메인 | 관리자)
   ├─ <Topbar>                            종목명 · 현재가 · 기준일 · Stale 배지
   └─ <main className="viewport-lock">    height: calc(100vh - 3.5rem)
      └─ <DashboardShell> grid-cols-12 grid-rows-6 gap-4
         ├─ <StaleBanner/>                col-span-12 (조건부)
         ├─ <SignalChartCard>             col-span-7 row-span-6
         │  ├─ <SignalChart/>             lightweight-charts (Candlestick + Area band)
         │  └─ <SignalMarkerPopover/>     마커 클릭 → 산출 근거
         └─ <RightStack> col-span-5 row-span-6
            ├─ <SentimentGauge/>          row-span-2 (반원 게이지)
            ├─ <KeywordTrend/>            row-span-1 (상위 키워드 칩)
            ├─ <FinancialSummary/>        row-span-2 (5지표 카드 그리드)
            └─ <CyclePanel/>              row-span-1 (Progress + 라벨)
```

### 데이터 흐름

```
SQLite (db/semi_senti.sqlite)
        ↓  read-only
 web/lib/db.ts  (sql.js WASM 싱글톤)
        ↓
 web/lib/snapshot.ts  (Python DashboardSnapshot 동일 shape 빌드)
        ↓
 app/api/snapshot/[code]/route.ts  (no-store)
        ↓
 hooks/use-snapshot.ts  (SWR · refreshInterval=300s · T-034)
        ↓
 <DashboardShell snapshot={...}>
        ↓ (props 1단계 drilling — 전역 store 불필요)
 각 카드는 자기 슬라이스만 소비
```

### 상태 관리 (Zustand/Redux 불필요)
| 상태 | 보관 |
|---|---|
| 선택 종목 코드 | URL `?code=005930` (App Router `searchParams`) |
| 스냅샷 데이터 | SWR 캐시 (key=`/api/snapshot/{code}`) |
| 갱신 주기 / On-Off | URL 또는 localStorage |
| 모달/팝오버 상태 | Radix uncontrolled |

---

## 5. 디자인 토큰 (확정 — `web/tailwind.config.ts` + `web/app/globals.css`)

### Shadcn HSL 변수 (다크 기준)
```css
.dark {
  --background: 240 10% 3.9%;   /* zinc-950 */
  --foreground: 0 0% 98%;
  --card: 240 6% 10%;            /* zinc-900 */
  --card-foreground: 0 0% 98%;
  --popover: 240 6% 8%;
  --border: 240 4% 16%;          /* zinc-800 */
  --muted: 240 4% 14%;
  --muted-foreground: 240 5% 65%; /* zinc-400 */
  --primary: 0 0% 98%;
  --secondary: 240 4% 16%;
  --destructive: 0 72% 51%;
  --ring: 240 5% 84%;
  --radius: 0.75rem;
}
```

### 시맨틱 시그널 토큰 (다크 기준)
```css
.dark {
  --signal-buy: 158 70% 48%;          /* emerald */
  --signal-sell: 350 89% 65%;         /* rose */
  --signal-hold: 240 5% 60%;          /* zinc */
  --divergence-bullish: 38 95% 56%;   /* amber */
  --divergence-bearish: 262 85% 66%;  /* violet */
  --sentiment-fear: 350 89% 65%;
  --sentiment-neutral: 240 5% 64%;
  --sentiment-greed: 158 70% 48%;
}
```

→ Tailwind 클래스: `bg-signal-buy`, `text-signal-sell`, `border-divergence-bullish` 등.

### 유틸 클래스
- `.glass-card` — Glassmorphism 카드 (border/border + backdrop-blur + 그라디언트 백드롭)
- `.viewport-lock` — `height: calc(100vh - 3.5rem); overflow: hidden;`

---

## 6. 진행 현황 (Tasks 매핑)

`docs/Tasks.md` Phase 5 섹션 — 진행률 `7 / 11`.

| ID | 상태 | 작업 |
|---|---|---|
| **T-048** | ✅ | `web/` 워크스페이스 신설 (스캐폴드 + 디자인 토큰) |
| **T-049** | ✅ | Shadcn UI 원시 컴포넌트 설치 (button/card/select/tabs/popover/tooltip/dialog/switch/slider/badge/skeleton) |
| **T-050** | ✅ | `AppShell` / `Sidebar` / `Topbar` / `DashboardShell` 골격 (1화면 집중) + `StockSelector` |
| **T-051** | ✅ | `web/lib/db.ts` (`sql.js` WASM read-only 싱글톤) |
| **T-052** | ✅ | `web/lib/snapshot.ts` (DashboardSnapshot 빌더; 다이버전스·실시간 밴드는 Python 엔진과 100% 동일하지 않음 — 비고) |
| **T-053** | ✅ | Route Handler `/api/stocks` · `/api/snapshot/[code]` · `/api/health` |
| **T-054** | ✅ | `hooks/use-snapshot` · `use-stocks` · `use-auto-refresh` (SWR) |
| T-055 | ⬜ | `SentimentGauge` / `KeywordTrend` / `FinancialSummary` / `CyclePanel` / `StaleBanner` / `DivergenceBadge` |
| T-056 | ⬜ | `SignalChart` (lightweight-charts) + `SignalMarkerPopover` |
| T-057 | ⬜ | `/admin` 페이지 — 종목 CRUD + 시스템 모니터 |
| T-058 | ⬜ | (조건부) `src/semi_senti/api/` FastAPI 어댑터 — 분석 엔진 트리거가 필요해질 때만 |

### 권장 진행 순서 (작업 효율 우선)
1. **F-2 = T-049 + T-050** (UI 셸 + Shadcn) — ✅
2. **F-3 = T-051 ~ T-054** (데이터 레이어) — ✅
3. **F-4 = T-055** (작은 카드들) — 차트 전 빠른 시각 검증
4. **F-5 = T-056** (SignalChart) — 가장 비싼 컴포넌트 마지막
5. **F-6 = T-057** (관리자)
6. **F-7 = T-058** (FastAPI, 조건부)

---

## 7. 미해결 결정 사항 (다음 채팅에서 확인 필요)

| # | 항목 | 현재 결정 | 검토 필요성 |
|---|---|---|---|
| 1 | Next.js 14 vs 15 | **14.2.5 고정** (안정성) | Next 15 + React 19로 마이그할지는 차후 |
| 2 | 데이터 어댑터 | **Route Handler가 SQLite 직접 read-only 조회** | 분석 엔진 신규 호출이 필요해지면 FastAPI(T-058) 추가 |
| 3 | `tailwind.config.js` vs `.ts` | **`.ts`** (Next.js+TS 표준 관행) | 사용자 원문은 `.js`였음 — 필요 시 `.js`로 변환 가능 |
| 4 | Node.js 버전 | **20+ (24 지원 확인됨)** | `sql.js` 사용으로 네이티브 빌드 불필요 |
| 5 | i18n 라이브러리 | 미정 | `next-intl` 또는 `react-intl` — 필요해지는 시점에 결정 |

---

## 8. 사용자가 다음 채팅 시작 전에 해야 할 일

```powershell
cd web
copy .env.local.example .env.local
npm install        # sql.js 사용 — 네이티브 빌드 불필요
npm run typecheck  # 0 error 기대
npm run dev        # http://localhost:3000 → 컬러 스와치 6개 보이면 OK
```

**에러가 나면** 그 로그를 그대로 다음 채팅 첫 프롬프트에 붙여 주세요.

---

## 9. 다음 채팅 시작용 프롬프트 템플릿

> 아래 블록을 그대로 새 채팅 첫 메시지로 붙여 넣으면 됩니다.

```text
@docs/handoff/2026-05-17-phase5-frontend-renewal.md @docs/Tasks.md @docs/PRD.md

위 핸드오프 문서를 읽고 Phase 5 작업을 이어서 진행해줘.

현재 상태:
- T-048 (스캐폴드) ✅ 완료, 커밋 c8106ad
- 다음 단계: T-049 (Shadcn 원시 컴포넌트 설치) + T-050 (AppShell/Sidebar/Topbar/DashboardShell 골격)

요청:
1. T-049 — Shadcn UI 원시 컴포넌트 11종을 web/components/ui/ 에 직접 추가해줘
   (button, card, select, tabs, popover, tooltip, dialog, switch, slider, badge, skeleton)
   ※ Shadcn CLI(npx shadcn-ui add ...) 대신 본문 코드를 직접 파일로 생성하는 방식으로.
2. T-050 — components/layout/{app-shell,sidebar,topbar}.tsx + components/dashboard/dashboard-shell.tsx 의 골격을 잡아줘.
   - 1화면 집중 (.viewport-lock)
   - grid-cols-12 grid-rows-6
   - 좌(차트) 7칸 / 우(스택) 5칸
   - 데이터는 mock 으로 placeholder 박스 채워두기
3. app/page.tsx 를 placeholder 컬러 스와치 → DashboardShell 호출로 교체
4. 작업 후 docs/Tasks.md 진행률 갱신 (T-049, T-050 ✅) 및 git 커밋·push

규칙:
- web/lib/types.ts 의 DashboardSnapshot 타입을 그대로 사용 (백엔드 DTO와 동일 shape)
- 시맨틱 토큰만 사용 (bg-signal-buy 등) — 직접 hex/oklch 색상 금지
- 한글 텍스트는 i18n 대비해서 상수 또는 메시지 키로 추출 가능한 형태로
- 커밋 메시지 형식: feat(web): T-049 ... / feat(web): T-050 ...
```

---

## 10. 참고 — 이전 답변에서 인용한 PRD/Tasks/Code 핵심

> **PRD §4.3 1화면 집중:** "종목 선택 후 캔들 차트, 감성 게이지, 재무 요약이 **스크롤 없이** 한 뷰포트 안에 표시되어야 한다."

> **PRD §F-3.2 시그널 로직:** `IF 현재가 < Band_Low AND Sentiment Score < -70 THEN BUY ... ELSE IF 현재가 > Band_High AND Sentiment Score > +70 THEN SELL ... ELSE HOLD`

> **백엔드 DTO (`data_provider.py`):** `DashboardSnapshot ... candles / signals / divergences / sentiment / financial / band / stale` — 이미 UI 한 화면 단위로 가공된 DTO를 백엔드가 제공함. 프론트엔드 타입은 이를 1:1 미러링.

---

## 11. 마지막 커밋 정보

```
commit c8106ad (HEAD -> main, origin/main)
feat(web): T-048 Next.js 14 frontend scaffold for Phase 5 renewal

20 files changed, 832 insertions(+), 13 deletions(-)
- web/{package.json, tsconfig.json, next.config.mjs, postcss.config.mjs,
       tailwind.config.ts, components.json, .gitignore, .env.local.example,
       README.md, app/{layout.tsx, globals.css, page.tsx},
       lib/{types.ts, utils.ts}}
- docs/{Tasks.md, PRD.md, UseCases.md, prompt-logs/2026-05-17.md}
- README.md
- .gitignore (lib/ → /lib/, .env.local.example negation)
```

**Push 상태:** `origin/main` 동기화 완료 (`79d08cf..c8106ad`).
