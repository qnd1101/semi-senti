/**
 * Semi Senti — 메인 대시보드 (placeholder).
 *
 * 이 페이지는 1단계 스캐폴드의 동작 확인용이며,
 * 다음 단계에서 다음 컴포넌트로 교체된다:
 *   <AppShell>
 *     <Sidebar/> <Topbar/>
 *     <DashboardShell snapshot={snapshot}/>
 *   </AppShell>
 *
 * 색상 토큰/레이아웃 토큰의 시각 확인만을 목적으로 한다.
 */
export default function HomePage() {
  return (
    <main className="viewport-lock">
      <div className="container flex h-full flex-col justify-center gap-8 py-12">
        <header className="space-y-2">
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
            Semi Senti · Frontend Renewal · Phase 0
          </p>
          <h1 className="text-3xl font-semibold tracking-tight">
            반도체 감성 + 펀더멘털 시그널 대시보드
          </h1>
          <p className="max-w-2xl text-sm text-muted-foreground">
            본 화면은 Next.js · Tailwind · Shadcn UI 기반 리뉴얼의 초기 스캐폴드입니다.
            다음 단계에서 차트·게이지·재무 카드가 채워집니다.
          </p>
        </header>

        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <ThemeSwatch label="BUY / Greed" tone="bg-signal-buy" />
          <ThemeSwatch label="SELL / Fear" tone="bg-signal-sell" />
          <ThemeSwatch label="HOLD / Neutral" tone="bg-signal-hold" />
          <ThemeSwatch
            label="Divergence · Bullish"
            tone="bg-divergence-bullish"
          />
          <ThemeSwatch
            label="Divergence · Bearish"
            tone="bg-divergence-bearish"
          />
          <ThemeSwatch label="Card surface" tone="bg-card border border-border" />
        </section>
      </div>
    </main>
  );
}

function ThemeSwatch({ label, tone }: { label: string; tone: string }) {
  return (
    <div className="glass-card p-5">
      <div className={`h-12 w-full rounded-md ${tone}`} aria-hidden />
      <div className="mt-3 flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className="text-xs text-muted-foreground">token</span>
      </div>
    </div>
  );
}
