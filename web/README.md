# Semi Senti — Web (Next.js Frontend)

Next.js 14 + Tailwind + Shadcn UI 기반의 **Claude 스타일** 대시보드 리뉴얼 워크스페이스입니다.
기존 Python 백엔드(`src/semi_senti/`)는 그대로 유지되며, 본 워크스페이스는
SQLite(`db/semi_senti.sqlite`)를 read-only로 공유합니다.

## Quick Start

```powershell
cd web
copy .env.local.example .env.local
npm install
npm run dev    # http://localhost:3000
```

> Node.js **18.18+** (권장 20 LTS) · npm 9+ 이 필요합니다.

## Scripts

| 명령 | 설명 |
|---|---|
| `npm run dev` | 개발 서버 (HMR) |
| `npm run build` | 프로덕션 빌드 |
| `npm start` | 프로덕션 서버 |
| `npm run lint` | ESLint |
| `npm run typecheck` | `tsc --noEmit` 타입체크 |

## Directory

```
web/
├─ app/           # App Router (layout / page / api routes)
├─ components/    # ui (shadcn) / dashboard / admin / layout
├─ hooks/         # SWR 기반 데이터 훅
├─ lib/           # db, snapshot, types, utils
├─ tailwind.config.ts
├─ components.json   # Shadcn CLI
└─ ...
```

## 디자인 토큰

- 다크 기본(`html.dark` 강제) · Zinc-950 베이스 · Glassmorphism 카드
- 시맨틱 토큰
  - `bg-signal-buy`  (emerald) · BUY / Greed
  - `bg-signal-sell` (rose)    · SELL / Fear
  - `bg-signal-hold` (zinc)    · HOLD / Neutral
  - `bg-divergence-bullish` (amber)  · 강세 다이버전스
  - `bg-divergence-bearish` (violet) · 약세 다이버전스

자세한 색상 코딩 규약은 `docs/PRD.md` §4.3 을 참고하세요.
